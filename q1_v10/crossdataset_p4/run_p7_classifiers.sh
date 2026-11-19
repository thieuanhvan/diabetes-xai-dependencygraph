#!/bin/sh
# Classifier robustness chain for one classifier: DiCE random on all surveys, then exhaustive search.
# Usage: sh run_p7_classifiers.sh lr|rf|xgbbrfss
cd "$(dirname "$0")"
V=/c/Repos/uit/diabetes-xai-counterfactual/.venv/Scripts/python.exe
O=/d/20-study/uit/research/diabetesxai/paper7/outputs/crossdataset_p4
C=$1
if [ "$C" = "xgbbrfss" ]; then
  # 11/11/2026: dropped for run time. XGBoost BRFSS DiCE random values come from the conference runner
  # (main Table 2). Random Forest BRFSS seeds 31337 and 7 were run in parallel (tags _rfb, _rfc) and merged by p7_classifier_tables.py.
  exit 0
fi
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
DS="nhanes2021-2023_a1c nhanes2021-2023_diag nhanes2017-2020_a1c nhanes2017-2020_diag nhis2022 nhis2024 brfss2021"
for d in $DS; do
  echo "### $d $C exhaustive $(date +%H:%M)" >> $O/run_log_clf_$C.txt
  $V -I p7_cross_classifiers.py --clf $C --gen exhaustive --dataset $d --tag _${C}_exh >> $O/run_log_clf_$C.txt 2>> $O/run_err_clf_$C.txt
done
for d in $DS; do
  echo "### $d $C random $(date +%H:%M)" >> $O/run_log_clf_$C.txt
  $V -I p7_cross_classifiers.py --clf $C --gen random --dataset $d --tag _$C >> $O/run_log_clf_$C.txt 2>> $O/run_err_clf_$C.txt
done
echo "### done $(date +%H:%M)" >> $O/run_log_clf_$C.txt
