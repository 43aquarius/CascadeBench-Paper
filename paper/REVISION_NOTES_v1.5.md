# REVISION NOTES v1.5 — 逐条回应审稿意见

对应稿件：CascadeBench v1.5（main 70 页 + supplementary 7 页）
本轮意见基于 v1.4 稿（77 页）。v1.4 稿件源文件随环境重置丢失，本轮以 v1.3 源为基线，
从原始日志完整重建 v1.4 的全部实验内容，并在重建中直接落实全部八条意见。
所有数字均由持久化脚本从原始 JSONL 日志重算（见 scripts/v15_*.py 与 results_real/analysis_v15_*.json）。

---

## 第一条：调用总数不一致（38,494 vs 41,854）——已统一

- **根因核实**：两口径的差异 3,360 = rev-mit 两行（ASR 1,680 + 级联 1,680），与您的回算一致；
  但重算发现 **两个口径还都漏计了 1,192 次 GLM 调用**（480 合成参考 + 150 真实参考 + 562 真实语音重译）。
- **统一口径（successful calls 约定，与 v1.3 延续）**：
  26,238（原测量）+ 5,581（扩展）+ 6,675（真实验证：4,650 核心 + 2,025 六级 babble 扩展）
  + 3,360（实测 RIR 桥接，合成语料）+ 1,192（第二厂商 GLM）= **43,046**
  （unique evaluations = 42,171）。摘要、§3.7、数据声明三处同步为 43,046。
- **Table 2 重构**：rev-mit 两行从 "Real validation" 移出，独立成
  "Measured-RIR bridge" 段（明确其为合成语料 + 实测脉冲响应条件）；GLM 独立成
  "Second vendor" 段；Whisper 600 次为本地运行、无 API 成本，单列表注。
- **"480 utts × 4 ASR" 标签澄清**：改为 "480 utts × 3 + 240 zh (8 kHz)"，
  级联行明确 "incl. 240 8 kHz translations"（Paraformer-8K 的 240 条 zh 翻译计入并写明）。
- 失败调用数重算：3,874 = 3,333（LiveTranslate websocket 掉线）+ 541（API 级失败），
  替换 v1.3 的 1,820 旧数（该数未含掉线会话与新阶段失败）。

## 第二条："Omni 最脆弱"与 Table 5 矛盾——已加范围限定

四处（5.1 指导、4.9 延迟段、5.2 再议、结论）全部改为有范围限定的表述：
- 统一措辞："**the most fragile of the end-to-end paths**（E2E 路径中最脆弱）"
  + "degrades more than the LLM-frontend cascades in point estimate（点估计上比 LLM 前端级联损失更大），
  with a reference-dependent margin"。
- 保留并强化参考依赖限定：点估计下 Omni 相对损失 33/29/30（primary/oracle/GLM）对
  LLM 级联 18–19/24–29/17–23；oracle 参考下与 Qwen3 级联差距不足一个点（29.0 对 29.5）。
- **新增配对 bootstrap（共同子集 n=82–84，300 次重采样）**：
  - 相对损失差（Omni − 级联）：primary +22.0 [8.7, 32.9] 显著；**oracle +11.7 [−5.6, +25.8] 跨零**；
    GLM +20.3 [6.5, 31.7] 显著（vs Qwen3：+21.8 / **+4.4 [−9.2, +18.4] 跨零** / +15.4）
  - 绝对 BLEU 差：primary −1.4 [−9.4, +5.9] 跨零；oracle −43.3（同引擎偏置所致）；GLM −1.7 [−10.0, +6.3] 跨零
  - 全部数字见新增 Supplementary Table S12

## 第三条：三参考排序稳定需加限定——摘要与结论已补

- §4.6（原已承认）、摘要、结论三处统一为："排序在三参考下稳定，
  **除 oracle（同引擎）参考下 Omni（29.0）与 Qwen3 级联（29.5）互换相邻位置、相差不足一个点**"
  （"sub-point inversion under the same-engine reference"）。
- 删除 v1.3 的"ordering preserved under both references"绝对化表述。

## 第四条：脱离厂商措辞过强——已全面收紧

- **GLM 实验**：所有 "no component in common with the vendor"、"all-external cascade" 删除。
  新表述（新 §4.8 开篇即声明）："the validation isolates the engine contribution to the
  pass-through, and **it does not constitute a vendor-independent cascade, since the
  recognition stage is still the provider's audio-LLM**"（验证隔离的是引擎贡献；
  前端仍是该厂商，不构成脱离厂商的级联）。摘要中相应表述为
  "a second vendor's translation engine"（第二厂商翻译引擎），不再声称整机脱离。
- **Whisper-small**：删除 "knee 结构复现" 类表述。新表述明确：
  "其 10% 交叉点在 +5 dB（所测最轻条件）之上，**膝点位置无法在测试范围内定位；
  数据对该模型的膝结构既不证实也不证伪**"；它支持的是"**高误差区的插入式幻觉**
  （zh 插入:删除 = 244:83，含逐字重复循环样本）"，且空转写率 5.3%→25.3%。
- **language-asymmetric 收窄为失败结构**：全文（4.4、5.2、局限、结论）改为
  "**Mandarin-insertion-dominated, English-deletion-dominated failure structure**（普通话插入主导、
  英文删除主导的失败结构）跨引擎复现；而语言间耐噪水平是引擎属性而非普遍规律
  （厂商 LLM 系统普通话更耐噪，Whisper 普通话在 +5 dB 即 78.7% 对英文 19.3%，方向相反）"。
- **传递规律去单引擎化**（对应您建议的升级项二，部分落实）：GLM 后端重译真实语音四条件，
  同引擎对角格子比跨引擎格子高 23–36 BLEU（亲和度在真实语音侧的度量）；
  两后端相对损失轨迹几乎重合（0 dB：33.7% 对 33.9%；−5 dB：89.4% 对 87.3%）；
  GLM 后端传递斜率 0.34/0.55 对厂商引擎同条件 0.38/0.72——**规律跨引擎成立、系数非引擎无关**。
  主网格"calibrated on one translation engine"限定改为指向该验证。
  局限中如实写明：仅一个前端、三个非干净工作点。
- 您建议的"Whisper large-v3 全六级跑一遍"未执行（本地资源与额度受限），
  已在 future work 与局限中明确为首要后续项。

## 第五条：各处小不一致——全部统一

1. **真实语音斜率**：以九条件（clean/rev/六级 babble/交通噪声）重拟合 =
   **0.43（zh, r=0.994）/ 0.72（en, r=0.999）**（旧 6 条件拟合复现为 0.413/0.724，
   与 v1.3 的 0.41/0.73 吻合，证实口径）。§4.4 与结论统一为 0.43/0.72，0.41 已删。
2. **dual → three**：Fig. 1（图内文字改为 "Three-reference scoring (2 vendors)"，重绘）、
   引言、§3.6（"Every hypothesis is scored against three reference sets"）、§4.4、§5.4、
   related.tex 定位段，全部改为三参考；全文无 "dual-reference"/"reference-invariant" 残留
   （自检项强制为 0）。
3. **Qwen3-ASR 阈值表述**：改为 "**优于两个专家系统**（两者在 +10 dB、所测最轻级即超 10%），
   **明显差于 Qwen-Audio**（2.8 dB 对 7.0 dB）"，并指出这是三点插值设计无法分辨的三方排序。
4. **Fig. 6 图注**：补 "The clean condition has zero loss by construction and is excluded
   from the fit, so the regression in the legend uses n=14, 14, and 11 points per cascade"，
   图例 n= 与图注 15/12 的矛盾消除；图内斜率标注字号 7.5→9，图例 8→9.5，画布缩小使印刷有效字号 ≥8pt。
5. **Fig. 5 字号**：分布图重绘（基准 10pt、画布 8.4in，印刷有效 ~9pt）；
   fig4/fig8 同步放大；fig4 图注 "hatched bar" 改为 "horizontal dashed line"（与新图一致）。

## 第六条：参考文献——逐条核对并修正

- **[14]（自训练论文）**：原条目 "Park, Jiho…, Robust self-training, ACL 2020, 2877–2882"
  **为错误条目**（未检索到该文）。已替换为正确文献：Pino, Xu, Ma, Dousti, Tang,
  "Self-Training for End-to-End Speech Translation", **Interserspeech 2020, 1476–1480,
  DOI 10.21437/Interspeech.2020-2938**（arXiv:2006.02490）——与您的记忆（Interspeech 2020）一致。
- **[25]（FunASR）**：原作者列表 "Gao, Zhang, **Li, Ming Lei**, Lei, McLoughlin" 有误。
  已按 ISCA 官方条目改为 10 作者：Gao, Li, Wang, Luo, Shi, Chen, Li, Zuo, Du, Zhang，
  页码 5314–5318 → **1593–1597**，补 **DOI 10.21437/Interspeech.2023-1428**。
- 删除两条未引用的损坏条目（"Jan, Zoltán…"、含 "Li, Ming Lei" 的 San-ASR 条目）。
- 新增：GLM-4.5 技术报告（arXiv:2508.06471）、GLM-4.6 模型卡（Z.ai，访问日期 2026-10）、
  qwen-mt-uni 模型卡（补齐 MT 引擎引用）。
- 其余条目抽查：traer2016（PNAS 113(48) E7856）、radford2023（ICML 28492–28518）、
  piczak2015（MM 1015–1018）、panayotov2015（ICASSP 5206–5210）、bu2017（APSIPA 520–524）、
  sperber2020（ACL DOI）、bentivogli2021（ACL-IJCNLP DOI）均无误。
  **注：GLM 的具体版本因 API key 已失效无法从日志复核，v1.5 采纳 v1.4 的版本无关表述
  （"GLM large language model, hosted API, Z.ai, accessed October 2026"）并引用 GLM-4.5
  技术报告作为家族背景，不再断言具体版本号。**

## 第七条：修订过程语言 / 摘要长度 / 附录 / 限定语密度

- **修订语言**：全文检索 "added in this revision / this revision / previous version /
  revision round" 等，正文已清零（唯一保留处为 Elsevier 要求的生成式 AI 使用声明）。
- **摘要**：360 词 → **256 词**（含三参考、实测 RIR、六级 babble、第二引擎等新内容，
  全部限定语保留）。
- **附录拆分**：D（配对显著性）、E（severity sweep 数值 + LT 前端）、F（拒答）、
  G（真实语音完整数值）移入独立 **supplementary.pdf（7 页，S1–S12 表）**，
  主文档保留 A–C（语料、定性错误、归一化协议）。主文 70 页（v1.4 为 77 页）。
  补充材料另含新增表：S5 九条件真实语音 ASR + cross-10% 列、S7 Whisper 明细 +
  插入/删除分解、S8 rev-mit ASR/级联、S9 三参考绝对分 + 配对检验。
- **限定语集中**：核心结论（摘要五句、结论五条）以限定但清晰的陈述给出；
  密集限定语集中到 Limitations（重写：单厂商主网格 / Whisper 2023 年小模型仅四条件 /
  GLM 后端仅三工作点 / 全部级联前端仍属该厂商 / 三参考仍为机器生成、无人工参考与 COMET）。
  全文维持"单厂商案例研究"定位，标题、摘要、结论无泛化措辞恢复。

## 第八条：结构性问题与升级项

定位与措辞维持"案例研究"，泛化措辞无恢复；升级项落实情况（按您给定的性价比序）：
1. **非阿里 ASR 全六级曲线**：未执行（无可用商用凭证；Whisper 本地仅四条件）——列为 future work 首位。
2. **GLM 后端重译 + 重拟合传递斜率**：✅ 已执行（四条件、一个前端；斜率 0.34/0.55 对 0.38/0.72）。
3. **人工参考 100–150 句**：❌ 无法执行（需双语人工），保持局限中首位缺口。
4. **真实 babble 补点**：✅ 已执行——六级阶梯（+10/+5/+2.5/0/−2.5/−5），膝点从插值变为实测。
5. （上轮已执行的 rev-mit 桥接条件）本轮完成核验并写入 §4.4 与补充材料 S8。

## 数字核验说明（对照原始日志）

您回算的全部数字对照原始 JSONL 重算，**全部命中**：
- rev-mit 两行 = 1,680 + 1,680 ✓；Paraformer 0 dB 相对损失 69/80/73 ✓；Omni 33/29/30 ✓；
  oracle 下 Omni 29.0 对 Qwen3 级联 29.5 ✓；Whisper zh/en 78.7/19.3 ✓；
  §4.4 斜率 0.43 ✓（九条件重拟合 0.429）；Fig. 6 图例 n=14/14/11 ✓（cac 数据本身不含 clean）。
- 新发现问题并已修正：GLM 1,192 次漏计（并入 43,046）；失败总数 1,820 → 3,874（口径拆分）；
  unique 总数 42,171。
- 全部重算脚本持久化于 scripts/v15_*.py；中间产物 results_real/analysis_v15_*.json 随仓库发布。

## 自检

67 项数字/措辞一致性自动检查全部通过（scripts/v15_selfcheck.py）；
tectonic 编译零错误、零未定义引用；Overfull 全部 ≤8pt（v1.3 为 ≤36pt）。
