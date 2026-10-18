# CascadeBench v1.3 修改说明（对 12 条审稿意见的逐条回应）

日期：2026-10-18 | 基础版本：v1.2（65 页）→ v1.3（69 页）

## 数字核验总则

所有数字类意见先对照原始 JSONL 日志重算（analysis_ext.py 重跑 + supplement_v13.py/supplement_v13b.py 新算），
用户回算的数字全部得到确认。重算产物：analysis_ext.json、supplement_v13.json、supplement_v13b.json。

## 第 1 条（参考偏置，最高优先级）—— 已修正

- 核验：oracle_self_bleu = 100（参考与级联 MT 引擎同源、引擎确定性）；真实 clean 级联 BLEU 69.1 vs E2E 42.0；
  ASR 前端与人工转写 133/150 句完全一致 → 31 分距离主要来自引擎对微小输入差异（标点/ITN）的措辞放大。
- 修改：
  - 4.4 节重写 E2E 段：绝对差距 27–28 分明确标注 same-engine artefact；改用 within-path 相对损失
    （级联 33.7% vs LiveTranslate 41.6%，参考不变量口径）支撑"E2E 不天然更鲁棒"。
  - 5.3 节删除"trails by 20 to 31 BLEU … understates the cascade advantage"，替换为同引擎偏置说明+相对损失。
  - 摘要、结论同步改为相对损失表述。
  - 2.7 节（方法）新增参考同源性警示段。
  - 附录 G.14 caption 加偏置提示。
  - 新增机制证据：133/150 一致 + self-BLEU 100 写入 4.4 节。
- 未做（需用户决策）：双语者人工参考 100–150 句、COMET 本地打分（unbabel-comet 下载未完成，网络受限）。

## 第 2 条（LLM 优势边界）—— 已修正

- 核验：zh 0dB Qwen3-ASR 117.5% vs Paraformer 102.6%；zh −5dB 207.6% vs 164.4%；en −5dB 86.6% vs 86.1%（全部属实）。
- 修改：4.4 节重写为"优势限定在 near-knee/低误差区间"叙述：Qwen3-ASR 在 +5dB 已过 10% 阈值（15.0%），
  幻觉区排序反转（0dB 与 −5dB 均劣于专家）；摘要与结论同步改写（"bounds the audio-LLM advantage to the
  near-knee regime"）。
- 新增：幻觉区插入/删除/替换拆分（合成+真实）：真实 −5dB zh 插入占比 q3 56%、q31 45%、para16k 37%、
  para8k 1.6%；en 全部删除主导（<12.4%）→ 插入幻觉主要是中文现象。
- 未做：补 +10/+2.5/−2.5dB 真实 SNR 点（需 ~900 次 API 调用，qwen-audio-3.0 额度仍可用，待用户确认后执行）。

## 第 3 条（电话频段混响脆弱性降级）—— 已修正

- 核验：真实混响 para8k 5.1→6.3%（合成 18.2%）。
- 修改：摘要删"uniquely fragile"句；5.1 节改为"proves specific to the synthetic extreme-DRR response:
  under three measured room impulse responses … degrades only from 5.1 to 6.3 percent"；
  结论与引言同步（"reverberation fragility … specific to synthetic extreme-DRR responses rather than real rooms"）。
- 注："loses 6.3%" 的歧义表述已消除（现在明确写 5.1→6.3 percent error）。

## 第 4 条（传递"定律"不确定性）—— 已修正

- 核验全部属实：q3 句子级 CI 0.35–0.60；排除 >40% 误差点后 0.44→0.37、0.54→0.68；真实斜率 0.41/0.73；
  q3 LOO 排除 n0 后斜率 0.47→0.74；摘要"±0.04"与 5.5 截距矛盾；56.5 应为 59.2。
- 修改：
  - 全文"law"→"empirical relation / rule of thumb"。
  - 3.8 节新增双口径不确定性声明（句子级 vs 条件层）。
  - 4.7 节重写：三大 caution（高误差点撑起相关、条件层 CI 0.23–0.45/0.52–0.66/0.38–3.9 重尾、
    线性有界）；q3 LOO 0.74 敞口如实报告。
  - 5.5 节算例：56.5→59.2；截距统一为"点估计 ±1 以内、统计上与零无异、保留仅为算术一致性"；
    删"±0.04 误差条"句；补有效域（误差 ≤60%）。
  - 摘要/结论/引言：删"±0.04"、"few hundredths"、"statistically zero intercept"→统一新表述。
  - 新增条件层 bootstrap（合成 3 级联 + 真实 zh/en，2000 次重采样）。

## 第 5 条（Table 4 与正文不一致）—— 已修正

- 核验：用户回算精确命中。条件级六点（20/15/10/5/2.5/0）OLS：q31 en = −1.31、q3 en = −1.06
  （论文原 −2.79/−2.64 错误；para16k zh −1.44/en −2.97、q31 zh −0.26、q3 zh −0.35、para8k −3.31 原值正确）。
  阈值差距：zh 2.2–2.5 dB（原文 2.4–2.9 错）、vs 电话专家 8.5–8.9（原文 7.6–8.9 错）、en 4.4–4.8（摘要 2.5–4 错）。
  论文 SNR@10% 列实为分段线性插值口径（interp10），max slope 为 logistic 外推。
- 修改：
  - Table 4 重建：OLS en 列改 −1.31/−1.06；新增"Steepest observed segment"列（13.0/15.2/9.9/23.7/12.6/18.7/13.5）；
    表注明确三口径（interp / logistic / segment）并声明 LLM 拐点位于 0~−5dB 无观测点区间。
  - 正文阈值差距改 2.2–2.5 与 8.5–8.9；摘要/引言/结论同步 2.2–2.5 与 4.4–4.8。
  - "专家系统在英文里退化得更快"修正后更成立（en OLS 专家 −2.97 vs LLM −1.06/−1.31）。
  - 修正后 OLS 表头口径 = E.10 六点条件级，完全可复现（analysis_ext.py slopes_v2）。
- 未做：补合成 −2.5dB 扫描点（432 次调用，待用户确认）。

## 第 6 条（STOI 变速指标误用）—— 已修正

- 修改：删除 tempo 0.16 例子；改为设计性说明（STOI/ESTOI 家族假设时间对齐，变速破坏该假设，故排除出
  跨家族比较）；新增 ESTOI 全条件数值（0.93/0.43/0.14 于 20/0/−10dB；rev 0.43）；"does not predict"表述
  收紧为跨家族解离+工程推论（"cannot infer API robustness from instrumental quality scores alone"）。
  3.8 节同步声明排除规则。

## 第 7 条（调用核算）—— 已修正

- 核验：原始阶段行和 25,387 vs 正文 26,238（差 851 = 表格用唯一评估口径、正文用成功调用口径，
  含 clip/pl/tempo 重跑 875 次）；扩展阶段实际成功 5,581（正文 7,609 无法从日志复现）；
  真实总数 36,469（非 38,497）；失败尝试 1,820（非 3,919）；"400+"实为 251/432。
- 修改：核算表重建为双列口径（successful calls / unique evaluations），逐行小计与总计 36,469/35,618
  可核对；正文 26,238/5,581/4,650/1,820 全部日志可复现；摘要 36,469；数据声明 36,469；"400+"→"251 of 432 targets"。

## 第 8 条（过期文字清扫）—— 已修正

- 新增 3.2 节术语定义（degradation family = 7 / degradation condition = 14 / operating point = 15）；
  摘要、引言、结论全部计数统一（eight-level sweep、fourteen conditions、three cascades）。
- "four/five translation designs/paths"→统一 five translation paths（4.5、5.1、结论）。
- Fig.4 图注（正文 Fig.5）："two cascades"→"two best cascades + 第三条以表格呈现"；"independent LLM
  reference"→"same-vendor LLM reference"；hatched bar 保留（图中有）。
- Fig.6 图注（正文 Fig.6）："fifteen conditions for three cascades"→"fifteen for two frontends, twelve for
  the Qwen3-ASR frontend"。
- "independent reference"→"same-vendor primary reference"（5.3）；"architectural families"→"product classes"（全文）。
- 4.5 节"within a point"→"within 1.1 BLEU points (mean gap 0.5, maximum at 0 dB) across the twelve shared
  conditions"（S8 重算 max=1.12）。
- 5.1 节"四种翻译设计"同步 five。

## 第 9 条（Table 5 无 CI + omni 子集）—— 已修正

- 修改：Table 5 加句子级 bootstrap 95% CI 列（300 次重采样）；正文新增共同子集分析：omni 84 句上 n0 的
  q31 级联 47.1 vs omni 45.5，配对差 CI [−11.3, +5.5] 跨零 →"omni 绝对分每条件最高"删除，改为
  "apparent lead is an artefact of two confounds"（子集+参考亲缘）；结论同步删除；
  caption 注明 omni 子集口径。3.8 节统计声明补 corpus-BLEU bootstrap CI 说明。
- 未做：omni 配额恢复后重跑验证 packet-loss/tempo 异常（配额未恢复）。

## 第 10 条（图排版）—— 已修复

- Fig.1：删除悬空箭头（原 arrow(9.5,30,9.5,25) 无目标）；全图字号 8.0→9.5、标题 12→13、箭头/边框加粗。
- Fig.4（正文 Fig.5）：图例 7.5→9pt（印刷尺寸可读）。
- 全部表格过宽问题修复（Overfull 130–184pt → ≤36pt）：Table 2/4/5 与核算表/附录表 footnotesize+收紧
  列距+两行式 CI+列头缩短。

## 第 11 条（参考文献）—— 已修正

- [25] chu2024qwen2audio / [26] qwen2.5omni2025：新增官方模型卡引用（qwenaudio31card/qwenomni38card，
  含 URL+版本+访问日期 2026-10），正文 2.4 节引用处并列。
- [31] qwen3technical2025："Yang, An and colleagues"→"Qwen Team"。
- [13] sperber2020speech：删除混入的期刊卷号/页码重复字段（保留 ACL 2020 7409–7421）。
- [15] yang2024airbench：ACL 62nd 1994–2018（错误出处）→ arXiv:2408.10513 + 完整作者。
- [16] chen2024voicebench：TACL 条目 → arXiv:2410.17196。
- 额外发现并修复：barker2018fifth 双逗号+重复 pages 字段（1561–1565 为正确值）；bentivogli2021cascade
  重复 pages（保留 2892–2903）；li2014overview 混入另一文章的卷号页码（更正为 TASLP 22(4):745–777）；
  hermansky1994rasta 误标 inproceedings→article。

## 第 12 条（匿名）—— 已核实并处理

- 查证：Applied Acoustics 采用**单盲评审**（single anonymized，Elsevier Guide for Authors 原文确认）。
- 处理：GitHub 实名链接保留；frontmatter 的"Anonymous Author / withheld for double-blind review"改为
  待填作者占位（`Author Name` + TODO 注释）；数据声明新增单盲说明。
- 建议：投稿前由通讯作者填入真实姓名与单位。

## 篇幅与档次（第 13 条可选）—— 部分完成

- 摘要 312→251 词（Elsevier ~250 达标）。
- 同批数字重复出现已压缩（引言/结论与第 4/5 节的数字现均为各自口径的必要引用）。
- 声学部分增强：3.8 节 ESTOI；4.2 节 STOI/ESTOI 曲线与跨家族解离的声学表述；术语定义节。
- 升档三项（多厂商 ASR、非阿里 MT、人工参考）未做——保持"单厂商案例研究"定位，泛化措辞已全面收紧
  （摘要/引言/结论/局限均明示 single-provider case study 与 cross-provider replication 前提）。

## 修改文件清单

- main.tex：摘要重写（251 词）、数据声明、作者占位、xurl
- intro.tex：计数统一、阈值、传递关系、混响限定
- methods.tex：术语定义节、参考同源警示、核算表重建（双列口径）、3.8 双口径不确定性、系统表收紧
- results.tex：Table 4 重建（OLS 修正+分段斜率列）、4.4 重写（优势边界+幻觉拆分+参考偏置）、
  Table 5 加 CI+共同子集、4.7 重写（三大 caution）、STOI/ESTOI 重写、图注修复
- discussion.tex：5.1/5.3/5.5 重写、five paths、混响降级、28 点补数字
- conclusions.tex：计数统一、五条结论全面校准
- appendix.tex：G.13 列合并、G.14 caption、CI 整数化、表格收紧
- refs.bib：9 处修正（见第 11 条）
- figures：fig1（悬空箭头+字号）、fig4（图例 9pt）重生成

## 重算数字对照表（关键值）

| 量 | v1.2 | v1.3（重算值） |
|---|---|---|
| q31 en OLS 20–0dB | −2.79 | **−1.31** |
| q3 en OLS 20–0dB | −2.64 | **−1.06** |
| zh 阈值差距 | 2.4–2.9 | **2.2–2.5** |
| vs 电话专家差距 | 7.6–8.9 | **8.5–8.9** |
| 摘要阈值差距 | 2.5–4 | **2.2–2.5 (zh) / 4.4–4.8 (en)** |
| 总成功调用 | 38,497 | **36,469** |
| 扩展阶段 | 7,609 | **5,581** |
| 失败尝试 | 3,919 | **1,820** |
| 5.5 专家 0dB 误差 | 56.5 | **59.2** |
| CAC CI | "±0.04" | **句子级 0.41–0.48；条件层 0.23–0.45（q31）** |
| E2E vs 级联（真实） | "落后 20–31 BLEU" | **绝对 27–28（same-engine 产物）；相对损失 41.6% vs 33.7%** |
| Omni n0 vs q31 级联 | "绝对分最高" | **共同子集 47.1 vs 45.5，配对 CI [−11.3,+5.5] 不显著** |
