#!/usr/bin/env bash
# v1.8.1 投稿资产: latex_source_v1.8.1.zip (含 figures, 修复 v1.7/v1.8 缺图缺陷) + 自包含编译验证
set -e
OUT=${OUT:-/tmp/latex_zip_out}
mkdir -p $OUT
STAGE=${STAGE:-/tmp/latex_zip_stage}
rm -rf $STAGE
mkdir -p $STAGE/latex_source_v1.8.1/latex $STAGE/latex_source_v1.8.1/figures

# latex tree (from repo, which now has the line-numbered main.tex)
cd "$(dirname "$0")/../paper/latex"
cp main.tex supplementary.tex refs.bib $STAGE/latex_source_v1.8.1/latex/
cp -r sections supp_tables $STAGE/latex_source_v1.8.1/latex/
rm -f $STAGE/latex_source_v1.8.1/latex/sections/*.aux 2>/dev/null || true

# figures: the 8 PDFs the manuscript includes
for f in fig1_architecture fig2_heatmap fig3_snr_curves fig4_cascade_e2e \
         fig5_distribution fig6_cac fig7_latency fig8_real_validation; do
  cp ../figures/$f.pdf $STAGE/latex_source_v1.8.1/figures/
done

# zip
rm -f $OUT/latex_source_v1.8.1.zip
cd $STAGE
zip -q -r $OUT/latex_source_v1.8.1.zip latex_source_v1.8.1
echo "zip: $(unzip -l $OUT/latex_source_v1.8.1.zip | tail -1)"

# self-contained compile test (fresh extract, no repo access)
TEST=${TEST:-/tmp/latex_zip_test}
rm -rf $TEST && mkdir $TEST
cd $TEST && unzip -q $OUT/latex_source_v1.8.1.zip
cd latex_source_v1.8.1/latex
tectonic main.tex 2>&1 | rg -v "warning: accessing absolute|lineno.sty" | tail -3
[ -f main.pdf ] && echo "SELF-CONTAINED COMPILE: OK ($(du -h main.pdf | cut -f1))" || { echo "COMPILE FAILED"; exit 1; }
tectonic supplementary.tex 2>&1 | rg -v "warning: accessing absolute" | tail -2
[ -f supplementary.pdf ] && echo "SUPP COMPILE: OK" || { echo "SUPP FAILED"; exit 1; }

# refresh the in-repo copy as well
cp $OUT/latex_source_v1.8.1.zip "$(dirname "$0")/../paper/latex_source.zip"
echo "repo paper/latex_source.zip refreshed"
