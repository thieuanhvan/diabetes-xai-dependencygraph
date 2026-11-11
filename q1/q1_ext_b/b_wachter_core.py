"""Wachter core for extension B (prereg v3 5.2, route 2 parity).

`wachter_recourse_edited` is CARLA's `wachter_recourse` (vendor/carla_24db00a/carla/recourse_methods/catalog/
wachter/library/wachter.py, commit 24db00aa8616eb2faedea0d6edf6e307cee9d192) with:
  (E1, required by prereg 5.2) the wall-clock stopping rule `t_max_min` removed; stopping uses the iteration
      cap only (n_iter per lambda step, lambda update `lamb -= 0.05` kept);
  (E2, deviation log B-D1) an outer cap `max_lambda_steps` on the number of lambda steps, because without the
      wall-clock rule the outer loop has no other exit when no valid point is reachable;
  (E3, deviation log B-D1) optional `x_init` (random start, prereg 5.3) and `project` (mask, direction/range
      projection and forced pattern moves, applied to x_new after every optimiser step, prereg 5.6).
With x_init=None, project=None and a non-binding max_lambda_steps the function follows the original line by
line (parity test in test_b.py). CARLA's `clamp` line is kept as in the original (it clamps a clone and has no
effect); the box is enforced by `project`.

`wachter_batch` runs R independent restarts of the same factual in one tensor (lock-step iteration counters,
per-row lambda and stopping), which equals R calls of `wachter_recourse_edited` up to floating-point summation
order; the parity test requires agreement within 1e-4 per coordinate (prereg 5.2 route 2), and the run script
re-checks it on real patients before the runs.
"""
from __future__ import annotations

from typing import Callable, List, Optional

import numpy as np
import torch
import torch.optim as optim
from torch.autograd import Variable

DECISION_THRESHOLD = 0.5


def reconstruct_encoding_constraints(x, feature_pos, binary_cat):
    """CARLA processing.counterfactuals.reconstruct_encoding_constraints, binary branch (verbatim logic)."""
    x_enc = x.clone()
    if binary_cat:
        for pos in feature_pos:
            x_enc[:, pos] = torch.round(x_enc[:, pos])
    else:
        raise NotImplementedError("one-hot pairs are not used in extension B")
    return x_enc


def wachter_recourse_edited(
    torch_model,
    x: np.ndarray,
    cat_feature_indices: List[int],
    binary_cat_features: bool,
    feature_costs: Optional[List[float]],
    lr: float,
    lambda_param: float,
    y_target: List[int],
    n_iter: int,
    norm: int,
    clamp: bool,
    loss_type: str,
    max_lambda_steps: int = 10**9,
    x_init: Optional[np.ndarray] = None,
    project: Optional[Callable[[torch.Tensor], torch.Tensor]] = None,
) -> np.ndarray:
    device = "cpu"
    torch.manual_seed(0)

    if feature_costs is not None:
        feature_costs = torch.from_numpy(feature_costs).float().to(device)

    x = torch.from_numpy(x).float().to(device)
    y_target = torch.tensor(y_target).float().to(device)
    lamb = torch.tensor(lambda_param).float().to(device)
    # E3: optional random start; the cost is always measured from the factual x
    x0 = x.clone() if x_init is None else torch.from_numpy(np.asarray(x_init).reshape(x.shape)).float().to(device)
    if project is not None:
        with torch.no_grad():
            x0 = project(x0)
    x_new = Variable(x0.clone(), requires_grad=True)
    x_new_enc = reconstruct_encoding_constraints(
        x_new, cat_feature_indices, binary_cat_features
    )

    optimizer = optim.Adam([x_new], lr, amsgrad=True)

    if loss_type == "MSE":
        if len(y_target) != 1:
            raise ValueError(f"y_target {y_target} is not a single logit score")
        target_class = int(y_target[0] > 0.0)
        loss_fn = torch.nn.MSELoss()
    elif loss_type == "BCE":
        if y_target[0] + y_target[1] != 1.0:
            raise ValueError(
                f"y_target {y_target} does not contain 2 valid class probabilities"
            )
        target_class = torch.round(y_target[1]).int()
        loss_fn = torch.nn.BCELoss()
    else:
        raise ValueError(f"loss_type {loss_type} not supported")

    f_x_new = torch_model(x_new)[:, target_class]

    n_lambda = 0  # E2
    while f_x_new <= DECISION_THRESHOLD:
        it = 0
        while f_x_new <= 0.5 and it < n_iter:
            optimizer.zero_grad()
            x_new_enc = reconstruct_encoding_constraints(
                x_new, cat_feature_indices, binary_cat_features
            )
            f_x_new = torch_model(x_new_enc)[:, target_class]

            if loss_type == "MSE":
                f_x_loss = torch.log(f_x_new / (1 - f_x_new))
            elif loss_type == "BCE":
                f_x_loss = torch_model(x_new_enc).squeeze(axis=0)
            else:
                raise ValueError(f"loss_type {loss_type} not supported")

            cost = (
                torch.dist(x_new_enc, x, norm)
                if feature_costs is None
                else torch.norm(feature_costs * (x_new_enc - x), norm)
            )

            loss = loss_fn(f_x_loss, y_target) + lamb * cost
            loss.backward()
            optimizer.step()
            if project is not None:  # E3
                with torch.no_grad():
                    x_new.copy_(project(x_new))
            if clamp:
                x_new.clone().clamp_(0, 1)
            it += 1
        lamb -= 0.05
        n_lambda += 1
        # E1: wall-clock rule removed. E2: lambda-step cap.
        if n_lambda >= max_lambda_steps:
            break
    return x_new_enc.cpu().detach().numpy().squeeze(axis=0)


def wachter_batch(
    torch_model,
    x: np.ndarray,
    x_init: np.ndarray,
    lo: np.ndarray,
    hi: np.ndarray,
    lr: float,
    lambda_param: float,
    y_target: List[int],
    n_iter: int,
    norm: int,
    max_lambda_steps: int,
    fixed: Optional[np.ndarray] = None,
    feature_costs: Optional[np.ndarray] = None,
    callback: Optional[Callable[[np.ndarray], None]] = None,
):
    """R restarts, BCE loss, no categorical encoding, no feature costs. x: one factual (d,) shared by all rows,
    or one factual per row (R, d) (several patients in one tensor; rows never interact). x_init, lo, hi, fixed: (R, d). Projection per row: coordinates with fixed=True are set to x; the others are
    clamped to [lo, hi]. Returns (points (R, d), pre-check valid flags (R,), iterations used (R,), lambda steps (R,))."""
    R, d = np.asarray(x_init).shape
    xr = np.asarray(x, dtype=np.float32)
    xr = np.repeat(xr.reshape(1, -1), R, axis=0) if xr.ndim == 1 else xr
    xt = torch.from_numpy(np.ascontiguousarray(xr)).float()
    lo_t = torch.from_numpy(np.asarray(lo, dtype=np.float32))
    hi_t = torch.from_numpy(np.asarray(hi, dtype=np.float32))
    fx = torch.zeros((R, d), dtype=torch.bool) if fixed is None else torch.from_numpy(np.asarray(fixed, bool))
    xb = xt

    def project(z):
        z = torch.minimum(torch.maximum(z, lo_t), hi_t)
        return torch.where(fx, xb, z)

    fc = None if feature_costs is None else torch.from_numpy(np.asarray(feature_costs, dtype=np.float32))
    torch.manual_seed(0)
    y_t = torch.tensor(y_target).float()
    target_class = int(torch.round(y_t[1]).int())
    yb = y_t.expand(R, 2)
    lamb = torch.full((R,), float(np.float32(lambda_param)), dtype=torch.float32)
    with torch.no_grad():
        x0 = project(torch.from_numpy(np.asarray(x_init, dtype=np.float32)))
    x_new = Variable(x0.clone(), requires_grad=True)
    optimizer = optim.Adam([x_new], lr, amsgrad=True)
    with torch.no_grad():
        f = torch_model(x_new)[:, target_class]
    result = x_new.detach().clone()
    active = (f <= DECISION_THRESHOLD).clone()
    valid = ~active
    iters = torch.zeros(R, dtype=torch.int64)
    lsteps = torch.zeros(R, dtype=torch.int64)
    n_lambda = 0
    while bool(active.any()) and n_lambda < max_lambda_steps:
        it = 0
        while bool(active.any()) and it < n_iter:
            optimizer.zero_grad()
            x_enc = x_new.clone()
            out = torch_model(x_enc)
            f = out[:, target_class]
            with torch.no_grad():
                result[active] = x_enc.detach()[active]
                newly = active & (f > DECISION_THRESHOLD)
                valid |= newly
                iters[active] += 1
                lsteps[active] = n_lambda
            bce = torch.nn.functional.binary_cross_entropy(out, yb, reduction="none").mean(dim=1)
            diff = x_enc - xb if fc is None else fc * (x_enc - xb)
            cost = torch.linalg.vector_norm(diff, ord=norm, dim=1)
            loss = ((bce + lamb * cost) * active.float()).sum()
            loss.backward()
            optimizer.step()
            with torch.no_grad():
                x_new.copy_(project(x_new))
            if callback is not None:
                callback(x_new.detach().numpy().copy())
            active = active & ~newly
            it += 1
        lamb = lamb - 0.05
        n_lambda += 1
    return result.numpy().astype(float), valid.numpy(), iters.numpy(), lsteps.numpy()
