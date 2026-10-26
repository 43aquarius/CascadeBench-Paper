#!/usr/bin/env bash
# v1.9.0 CSL submission asset: latex_source_v1.9.0.zip (with figures) + self-contained compile test
set -e
OUT=${OUT:-/tmp/latex_zip_out}
mkdir -p $OUT
STAGE=${STAGE:-/tmp/latex_zip_stage}
rm -rf $STAGE
mkdir -p $STAGE/latex_source_v1.9.0/latex $STAGE/latex_source_v1.9.0/figures

# latex tree (repo copy carries the CSL authoryear conversion)
cd "$(dirname "$0")/../paper/latex"
cp main.tex supplementary.tex refs.bib $STAGE/latex_source_v1.9.0/latex/
cp -r sections supp_tables $STAGE/latex_source_v1.9.0/latex/
rm -f $STAGE/latex_source_v1.9.0/latex/sections/*.aux 2>/dev/null || true

# figures: the 8 PDFs the manuscript includes
for f in fig1_architecture fig2_heatmap fig3_snr_curves fig4_cascade_e2e \
         fig5_distribution fig6_cac fig7_latency fig8_real_validation; do
  cp ../figures/$f.pdf $STAGE/latex_source_v1.9.0/figures/
done

# zip
rm -f $OUT/latex_source_v1.9.0.zip
cd $STAGE
zip -q -r $OUT/latex_source_v1.9.0.zip latex_source_v1.9.0
echo "zip: $(unzip -l $OUT/latex_source_v1.9.0.zip | tail -1)"

# self-contained compile test (fresh extract, no repo access)
TEST=${TEST:-/tmp/latex_zip_test}
rm -rf $TEST && mkdir $TEST
cd $TEST && unzip -q $OUT/latex_source_v1.9.0.zip
cd latex_source_v1.9.0/latex
tectonic main.tex 2>&1 | grep -v "warning: accessing absolute\|lineno.sty" | tail -3
[ -f main.pdf ] && echo "SELF-CONTAINED COMPILE: OK ($(du -h main.pdf | cut -f1))" || { echo "COMPILE FAILED"; exit 1; }
tectonic supplementary.tex 2>&1 | grep -v "warning: accessing absolute" | tail -2
[ -f supplementary.pdf ] && echo "SUPP COMPILE: OK" || { echo "SUPP FAILED"; exit 1; }
# authoryear sanity check on the fresh-extract build
pdftotext -f 1 -l 1 main.pdf - | grep -q "Computer Speech & Language" && echo "JOURNAL FOOTER: OK"
pdftotext main.pdf - | grep -qE "\(Pearce and Hirsch, 2000\)" && echo "AUTHOR-YEAR CITES: OK"

# refresh the in-repo copy as well
cp $OUT/latex_source_v1.9.0.zip "$(dirname "$0")/../paper/latex_source.zip"
echo "repo paper/latex_source.zip refreshed"
