/* ═══════════════════════════════════════════════════════════════
   vibe_proving — app.js  v3
   架构: AppState → UI.sync → DOM
   纯原生 JS，无构建步骤。
═══════════════════════════════════════════════════════════════ */

'use strict';

/* ─────────────────────────────────────────────────────────────
   1. 国际化（I18N）
───────────────────────────────────────────────────────────── */
const I18N = {
  zh: {
    nav: {
      playground: '主界面', projects: '项目',
      service: '服务状态', settings: '设置',
      workspace: '工作区', recent: '近期',
    },
    topbar: {
      title: '临时对话', pin: '保存', panel: '设置面板',
      pinTip: '保存到项目', themeTip: '切换主题', panelTip: '设置面板',
      homeTip: '返回主界面',
    },
    home: {
      title: 'vibe_proving',
      tagline: '数学工作者的推理伙伴',
      subTagline: '严谨 · 可验证 · 不逢迎',
      examples: '示例提示词',
      hintEnter: '按', hintSend: '发送', hintNewline: '换行', hintStop: '停止',
    },
    cards: {
      learning:       { title: '学习模式', desc: '为数学命题生成分步教学讲解，面向学生' },
      solving:        { title: '问题求解', desc: '自动证明数学命题，生成完整分步证明，置信度评估与主动拒绝' },
      reviewing:      { title: '证明审查', desc: '上传数学论文 PDF，AI 将逐步审查逻辑漏洞、引用的定理与符号一致性' },
      searching:      { title: '定理检索', desc: '直接搜索 1kw+ 定理库，获取定理的真实来源' },
      projects:       { title: '项目管理', desc: '保存、组织并随时回到你的研究项目' },
      history:        { title: '历史会话', desc: '浏览近期对话与提问记录，一键继续' },
      formalization:  { title: '形式化证明', desc: '将数学命题转化为 Lean 4 代码：搜索 mathlib4 · 自动形式化 · 本地编译验证' },
    },
    modes: {
      learning: '学习模式', solving: '问题求解',
      reviewing: '证明审查', searching: '定理检索',
      formalization: '形式化证明',
      aria: '选择模式',
    },
    models: { aria: '选择模型' },
    input: {
      placeholder: '输入数学命题...',
      proofUploadTip: '上传文件 (.pdf / .tex / .txt / .md)',
      attachTip: '上传论文或证明文件 (.pdf / .tex / .txt / .md)',
      proofPlaceholder: '点击 📎 上传 PDF 论文，或粘贴证明文本…',
      proofFocusPlaceholder: '可补充审查重点（可选）…',
      stop: '■ 停止', stopAria: '停止生成',
      sendTip: '发送 (↵)', sendAria: '发送', aria: '输入数学命题',
    },
    panel: {
      title: '运行设置', close: '关闭',
      appearance: '外观', theme: '主题', language: '语言',
      level: '学习层次', undergraduate: '本科', graduate: '研究生',
      params: '参数', stream: '流式输出', maxTheorems: '最大定理数',
      features: '功能', memory: 'LATRACE 记忆',
      citation: '引用核查', status: '服务状态',
      checkLogic: '审查逻辑漏洞', checkCitations: '核查定理引用', checkSymbols: '检查符号一致性',
      extendedThinking: '深度思考', extendedThinkingHint: '启用后模型会展示推理过程（仅 Claude）',
      shortcuts: '快捷键',
      skSend: '发送', skNewline: '换行', skStop: '停止生成',
      skFocus: '聚焦输入框', skMode: '切换模式',
    },
    modal: { projects: {
      title: '项目管理', new: '新建项目',
      namePlaceholder: '项目名称', descPlaceholder: '描述（可选）',
      create: '创建', cancel: '取消', use: '切换到此项目',
      selectHint: '选择一个项目查看详情',
      concepts: '知识概念', openQ: '开放问题', sessions: '会话记录',
      stateUnseen: '未接触', stateConfused: '有疑惑',
      stateUnderstood: '已理解', stateMastered: '已掌握',
      noConceptsHint: '还没有概念记录', noQuestionsHint: '还没有开放问题',
      noSessionsHint: '还没有会话记录',
      kb: '知识库', kbUpload: '上传文件', kbNoDoc: '拖拽文件到此处，或点击 ↑ 上传',
      kbConstrain: '仅在知识库内回答',
      kbDropHint: '拖拽文件到此处，或点击 ↑ 上传',
      kbDropSub: 'PDF · LaTeX · TXT · MD · 最大 20 MB',
      kbUploading: '上传中…', kbUploadOk: '上传成功', kbUploadFail: '上传失败：{e}',
      kbPreview: '预览', kbPreviewClose: '关闭',
      activeLabel: '当前使用中',
    } },
    ui: {
      status: { proved: '已证明', unproven: '未证明', partial: '部分成立',
                direct_hit: '直接命中',
                'no confident solution': '主动拒绝',
                unverifiable: '无法核查', error: '错误',
                confidence: '置信度', citations: '引用',
                memHint: '已检索 {n} 条历史知识' },
      accordion: { background: '数学背景', prereq: '前置知识', proof: '完整证明', examples: '具体例子', extensions: '延伸阅读' },
      search: { noResult: '未找到相关定理', similarity: '相关度' },
      review: { overall: '整体判定', theorem: '定理' },
      role: { user: '你', ai: 'AI' },
      project: { current: '当前项目', default: '默认项目' },
      thinking: '思考中',
      think: {
        live:     '正在推理',
        finished: '已思考',
        seconds:  '秒',
        tokens:   '字',
        showLabel: '展开思考',
        hideLabel: '收起思考',
      },
      copy: '复制', copied: '已复制', retry: '重试', stopped: '已停止',
      noHistory: '暂无历史', noProjects: '暂无项目',
      err: {
        network: '网络中断，请检查连接后重试',
        timeout: '请求超时，模型可能较忙，请稍后重试',
        learning: '学习模式失败：{e}',
        solving: '求解失败：{e}',
        reviewing: '证明审查失败：{e}',
        searching: '定理检索失败：{e}',
        formalization: '形式化失败：{e}',
        emptyProof: '请粘贴证明文本或上传文件',
        proofTooLong: '证明文本超过 50000 字符，请精简后再试',
        fileTooLarge: '文件大小超过 50KB，请精简后再上传',
        fileReadFailed: '文件读取失败：{e}',
        unsupportedFile: '暂不支持该文件类型，请上传 .tex / .txt / .md',
        copyFailed: '复制失败，请手动选择',
        projectCreated: '项目创建成功',
        projectFailed: '创建失败：{e}',
        projectMissing: '请填写项目 ID 和名称',
        savedSession: '对话已保存到历史',
        emptyChat: '当前没有对话内容',
      },
    },
    docs: {
      title: 'vibe_proving — 使用指南',
      btnTitle: '使用指南',
      heroPara: '严谨 · 可验证 · 不逢迎。将语言模型与形式化数学工具结合，为数学专业学生和研究者提供证明辅助、深度学习讲解、逻辑审查与定理检索。',
      modulesTitle: '四大核心模块',
      cards: [
        { icon: 'ℓ', title: '学习模式', body: '输入任意数学命题或定理，AI 自动生成：<br>• <strong>数学背景</strong>：历史脉络与意义<br>• <strong>完整证明</strong>：分步标注，每步说明 why<br>• <strong>具体例子</strong>：包含边界情形分析<br>• <strong>前置知识</strong>：理解该证明所需的概念清单' },
        { icon: '∂', title: '问题求解', body: '输入待证命题，AI 自动：<br>• 尝试直接证明（多轮修订循环）<br>• 反例测试（检验命题是否成立）<br>• 子目标分解（复杂命题拆分）<br>• 引用核查（TheoremSearch 验证）<br>• 置信度评估，低置信度时主动拒绝' },
        { icon: '¶', title: '证明审查', body: '粘贴或上传证明文本（.tex/.txt/.md），AI：<br>• 逐步核验每个推理步骤<br>• 标注 passed / gap / critical_error<br>• 检查引用定理是否真实存在<br>• 给出整体判定：Correct / Partial / Incorrect<br>支持 LaTeX 环境（\\begin{theorem}…）' },
        { icon: '∇', title: '定理检索', body: '直接搜索 1000 万+ 定理库：<br>• 自然语言查询（"Cauchy sequence convergence"）<br>• 返回定理名、slogan、来源论文、arXiv 链接<br>• 相似度排序，高质量结果排前<br>学习/求解模式自动调用此接口补充上下文' },
      ],
      kbTitle: '§ Project 知识库',
      kbDesc: 'Project 是长期研究的组织单位，每个 Project 拥有独立的：',
      steps: [
        { n: 1, title: '创建项目', body: '左侧导航点"项目"，或主界面点"项目管理"，输入 ID 和名称创建。' },
        { n: 2, title: '上传知识库', body: '在项目详情的 Knowledge Base 区域，拖拽或点击上传 PDF、LaTeX (.tex)、TXT、MD 文件（最大 20 MB）。上传后 AI 自动分块，写入项目记忆。' },
        { n: 3, title: '激活项目', body: '点击"Use this project"，此后所有对话都会先检索该项目的知识库，将相关段落注入模型上下文。' },
        { n: 4, title: 'KB Only 模式', body: '开启"KB only"开关，模型被要求仅在知识库范围内回答，适合考试复习或精读某本教材。' },
        { n: 5, title: '概念追踪', body: '手动记录每个概念的理解状态（未接触 → 有疑惑 → 已理解 → 已掌握），建立个人知识图谱。' },
        { n: 6, title: '开放问题', body: '记录学习过程中未解决的问题，下次进入项目时一键继续。' },
      ],
      tip: '切换模块时会自动选用最适合该任务的模型。也可在底部下拉手动切换。',
    },
  },
  en: {
    nav: {
      playground: 'Playground', projects: 'Projects',
      service: 'Service', settings: 'Settings',
      workspace: 'Workspace', recent: 'Recent',
    },
    topbar: {
      title: 'Temporary chat', pin: 'Save', panel: 'Settings',
      pinTip: 'Save to project', themeTip: 'Toggle theme', panelTip: 'Settings panel',
      homeTip: 'Back to home',
    },
    home: {
      title: 'vibe_proving',
      tagline: 'A reasoning companion',
      subTagline: 'Rigorous · Verifiable · Honest',
      examples: 'Example prompts',
      hintEnter: 'Press', hintSend: 'to send', hintNewline: 'newline', hintStop: 'stop',
    },
    cards: {
      learning:       { title: 'Learning Mode',  desc: 'Step-by-step pedagogical explanation of math proofs' },
      solving:        { title: 'Problem Solving', desc: 'Generates complete step-by-step proofs with confidence scoring and active refusal' },
      reviewing:      { title: 'Proof Review',    desc: 'Upload a math paper PDF; AI progressively reviews logic gaps, theorem citations, and symbol consistency' },
      searching:      { title: 'Theorem Search',  desc: 'Search 10M+ theorems and get real sources' },
      projects:       { title: 'Projects',        desc: 'Save, organize and resume your research projects' },
      history:        { title: 'History',         desc: 'Browse recent sessions and resume any conversation' },
      formalization:  { title: 'Formalization', desc: 'Convert math statements to Lean 4: search mathlib4 · auto-formalize · local compile verification' },
    },
    modes: {
      learning: 'Learning', solving: 'Solving',
      reviewing: 'Proof Review',  searching: 'Search',
      formalization: 'Formalization',
      aria: 'Select mode',
    },
    models: { aria: 'Select model' },
    input: {
      placeholder: 'Enter a math statement...',
      proofUploadTip: 'Upload file (.tex / .txt / .md)',
      attachTip: 'Attach paper or proof file (.pdf / .tex / .txt / .md)',
      proofPlaceholder: 'Click 📎 to upload PDF, or paste proof text…',
      proofFocusPlaceholder: 'Optional: add a review focus…',
      stop: '■ Stop', stopAria: 'Stop generation',
      sendTip: 'Send (↵)', sendAria: 'Send', aria: 'Math statement input',
    },
    panel: {
      title: 'Run settings', close: 'Close',
      appearance: 'Appearance', theme: 'Theme', language: 'Language',
      level: 'Level', undergraduate: 'Undergraduate', graduate: 'Graduate',
      params: 'Parameters', stream: 'Stream', maxTheorems: 'Max theorems',
      features: 'Features', memory: 'LATRACE Memory',
      citation: 'Citation check', status: 'Service',
      checkLogic: 'Check logic gaps', checkCitations: 'Verify citations', checkSymbols: 'Check symbols',
      extendedThinking: 'Extended thinking', extendedThinkingHint: 'Shows reasoning process (Claude only)',
      shortcuts: 'Shortcuts',
      skSend: 'Send', skNewline: 'Newline', skStop: 'Stop',
      skFocus: 'Focus input', skMode: 'Switch mode',
    },
    modal: { projects: {
      title: 'Projects', new: 'New project',
      namePlaceholder: 'Project name', descPlaceholder: 'Description (optional)',
      create: 'Create', cancel: 'Cancel', use: 'Use this project',
      selectHint: 'Select a project to view details',
      concepts: 'Concepts', openQ: 'Open Questions', sessions: 'Sessions',
      stateUnseen: 'Unseen', stateConfused: 'Confused',
      stateUnderstood: 'Understood', stateMastered: 'Mastered',
      noConceptsHint: 'No concepts yet', noQuestionsHint: 'No open questions yet',
      noSessionsHint: 'No sessions yet',
      kb: 'Knowledge Base', kbUpload: 'Upload', kbNoDoc: 'Drop files here or click ↑ to upload',
      kbConstrain: 'KB only',
      kbDropHint: 'Drop files here or click ↑ to upload',
      kbDropSub: 'PDF · LaTeX · TXT · MD · up to 20 MB',
      kbUploading: 'Uploading…', kbUploadOk: 'Uploaded', kbUploadFail: 'Upload failed: {e}',
      kbPreview: 'Preview', kbPreviewClose: 'Close',
      activeLabel: 'Active',
    } },
    ui: {
      status: { proved: 'Proved', unproven: 'Unproven', partial: 'Partial',
                direct_hit: 'Direct hit',
                'no confident solution': 'Refused',
                unverifiable: 'Unverifiable', error: 'Error',
                confidence: 'Confidence', citations: 'Citations',
                memHint: 'Retrieved {n} memories' },
      accordion: { background: 'Background', prereq: 'Prerequisites', proof: 'Complete Exposition', examples: 'Examples', extensions: 'Further reading' },
      search: { noResult: 'No theorems found', similarity: 'Similarity' },
      review: { overall: 'Overall verdict', theorem: 'Theorem' },
      role: { user: 'You', ai: 'AI' },
      project: { current: 'Project', default: 'Default' },
      thinking: 'Thinking',
      think: {
        live:     'Thinking',
        finished: 'Thought for',
        seconds:  's',
        tokens:   'chars',
        showLabel: 'Show thinking',
        hideLabel: 'Hide thinking',
      },
      copy: 'Copy', copied: 'Copied!', retry: 'Retry', stopped: 'Stopped',
      noHistory: 'No history yet', noProjects: 'No projects yet',
      err: {
        network: 'Network lost. Please check your connection and retry.',
        timeout: 'Request timed out. The model may be busy, try again shortly.',
        learning: 'Learning mode failed: {e}',
        solving: 'Solver failed: {e}',
        reviewing: 'Proof review failed: {e}',
        searching: 'Search failed: {e}',
        formalization: 'Formalization failed: {e}',
        emptyProof: 'Please paste a proof or upload a file',
        proofTooLong: 'Proof exceeds 50000 chars. Please trim it.',
        fileTooLarge: 'File exceeds 50KB. Please trim it before uploading.',
        fileReadFailed: 'Failed to read file: {e}',
        unsupportedFile: 'Unsupported file type. Use .tex / .txt / .md',
        copyFailed: 'Copy failed, please select manually',
        projectCreated: 'Project created',
        projectFailed: 'Failed: {e}',
        projectMissing: 'Project ID and name are required',
        savedSession: 'Conversation saved',
        emptyChat: 'Nothing to save yet',
      },
    },
    docs: {
      title: 'vibe_proving — User Guide',
      btnTitle: 'User Guide',
      heroPara: 'Rigorous · Verifiable · Honest. Combines language models with formal math tools to provide proof assistance, in-depth explanations, logic review, and theorem retrieval for math students and researchers.',
      modulesTitle: 'Four Core Modules',
      cards: [
        { icon: 'ℓ', title: 'Learning Mode', body: 'Enter any mathematical statement or theorem and AI generates:<br>• <strong>Background</strong>: historical context and significance<br>• <strong>Complete Proof</strong>: step-by-step with why at each step<br>• <strong>Examples</strong>: including boundary case analysis<br>• <strong>Further Reading</strong>: related theorems, open problems, exercises<br>• <strong>Prerequisites</strong>: concepts needed to understand the proof' },
        { icon: '∂', title: 'Problem Solving', body: 'Submit a statement to prove and AI automatically:<br>• Attempts direct proof (multi-round revision loop)<br>• Tests for counterexamples<br>• Decomposes into sub-goals<br>• Verifies citations via TheoremSearch<br>• Assigns confidence; actively refuses low-confidence results' },
        { icon: '¶', title: 'Proof Review', body: 'Paste or upload proof text (.tex/.txt/.md) and AI:<br>• Verifies each reasoning step<br>• Labels steps: passed / gap / critical_error<br>• Checks cited theorems for existence<br>• Issues overall verdict: Correct / Partial / Incorrect<br>Supports LaTeX environments (\\begin{theorem}…)' },
        { icon: '∇', title: 'Theorem Search', body: 'Search 10M+ theorem database directly:<br>• Natural language queries ("Cauchy sequence convergence")<br>• Returns theorem name, slogan, source paper, arXiv link<br>• Ranked by similarity, top results first<br>Learning/Solving modes call this automatically for context' },
      ],
      kbTitle: '§ Project Knowledge Base',
      kbDesc: 'A Project is a long-term research unit. Each project has its own:',
      steps: [
        { n: 1, title: 'Create a project', body: 'Click "Projects" in the sidebar or "Project Management" on the home screen. Enter an ID and name to create.' },
        { n: 2, title: 'Upload knowledge base', body: 'In the project\'s Knowledge Base section, drag or click to upload PDF, LaTeX (.tex), TXT, or MD files (max 20 MB). AI auto-chunks them into project memory.' },
        { n: 3, title: 'Activate project', body: 'Click "Use this project". All conversations will then retrieve from the project knowledge base and inject relevant passages into model context.' },
        { n: 4, title: 'KB Only mode', body: 'Enable "KB only" to restrict the model to answer only from the knowledge base — ideal for exam review or close reading of a specific text.' },
        { n: 5, title: 'Concept tracking', body: 'Manually record understanding state for each concept (Unseen → Confused → Understood → Mastered) to build your knowledge graph.' },
        { n: 6, title: 'Open questions', body: 'Record unresolved questions during study. Return to the project anytime and continue where you left off.' },
      ],
      tip: 'Switching modes automatically selects the most suitable model for the task. You can also manually switch via the bottom dropdown.',
    },
  },
};

const EXAMPLE_PROMPTS = {
  learning: {
    zh: [
      '证明：任意无穷集合存在可数子集',
      '解释柯西积分公式的几何意义',
      '证明：实数的完备性等价于有界数列必有收敛子列',
    ],
    en: [
      'Prove: every infinite set has a countably infinite subset',
      'Explain the geometric meaning of the Cauchy integral formula',
      'Prove the intermediate value theorem from first principles',
    ],
  },
  solving: {
    attribution: {
      zh: { text: '来自 First Proof 问题集', url: 'https://1stproof.org/first-batch.html' },
      en: { text: 'From the First Proof benchmark', url: 'https://1stproof.org/first-batch.html' },
    },
    zh: [
      {
        label: 'FP #4 · $p \\boxplus_n q$ 不等式',
        text: '设 $p(x)$ 和 $q(x)$ 是两个 $n$ 次首一多项式：\n$$p(x) = \\sum_{k=0}^{n} a_k x^{n-k}, \\quad q(x) = \\sum_{k=0}^{n} b_k x^{n-k},$$\n其中 $a_0 = b_0 = 1$。定义 $(p \\boxplus_n q)(x) = \\sum_{k=0}^{n} c_k x^{n-k}$，其中\n$$c_k = \\sum_{i+j=k} \\frac{(n-i)!(n-j)!}{n!(n-k)!} a_i b_j, \\quad k=0,1,\\ldots,n.$$\n对首一多项式 $p(x) = \\prod_{i \\leq n}(x - \\lambda_i)$，定义\n$$\\Phi_n(p) := \\left(\\sum_{i \\leq n} \\prod_{j \\neq i} \\frac{1}{\\lambda_i - \\lambda_j}\\right)^2,$$\n若 $p$ 有重根则 $\\Phi_n(p) := \\infty$。若 $p(x)$ 和 $q(x)$ 均为实根首一 $n$ 次多项式，是否有\n$$\\frac{1}{\\Phi_n(p \\boxplus_n q)} \\geq \\frac{1}{\\Phi_n(p)} + \\frac{1}{\\Phi_n(q)}?$$',
      },
      {
        label: 'FP #6 · $\\epsilon$-轻子集',
        text: '设图 $G = (V, E)$，令 $G_S = (V, E(S,S))$ 为顶点集相同但仅保留 $S$ 内部边的导出子图。设 $L$ 为 $G$ 的 Laplace 矩阵，$L_S$ 为 $G_S$ 的 Laplace 矩阵。称顶点子集 $S$ 是 $\\epsilon$-轻的，若矩阵 $\\epsilon L - L_S$ 是半正定的。是否存在常数 $c > 0$，使得对任意图 $G$ 和任意 $0 \\leq \\epsilon \\leq 1$，$V$ 中均含有大小至少为 $c\\epsilon|V|$ 的 $\\epsilon$-轻子集 $S$？',
      },
    ],
    en: [
      {
        label: 'FP #4 · $p \\boxplus_n q$ inequality',
        text: 'Let $p(x)$ and $q(x)$ be two monic polynomials of degree $n$:\n$$p(x) = \\sum_{k=0}^{n} a_k x^{n-k} \\quad \\text{and} \\quad q(x) = \\sum_{k=0}^{n} b_k x^{n-k},$$\nwhere $a_0 = b_0 = 1$. Define $(p \\boxplus_n q)(x) = \\sum_{k=0}^{n} c_k x^{n-k}$ where\n$$c_k = \\sum_{i+j=k} \\frac{(n-i)!(n-j)!}{n!(n-k)!} a_i b_j \\quad \\text{for } k = 0,1,\\dots,n.$$\nFor a monic polynomial $p(x) = \\prod_{i \\leq n} (x - \\lambda_i)$, define\n$$\\Phi_n(p) := \\left( \\sum_{i \\leq n} \\prod_{j \\neq i} \\frac{1}{\\lambda_i - \\lambda_j} \\right)^2$$\nand $\\Phi_n(p) := \\infty$ if $p$ has a multiple root. Is it true that if $p(x)$ and $q(x)$ are monic real-rooted polynomials of degree $n$, then\n$$\\frac{1}{\\Phi_n(p \\boxplus_n q)} \\geq \\frac{1}{\\Phi_n(p)} + \\frac{1}{\\Phi_n(q)} \\; ?$$',
      },
      {
        label: 'FP #6 · $\\epsilon$-light subsets',
        text: 'For a graph $G = (V, E)$, let $G_S = (V, E(S,S))$ denote the graph with the same vertex set, but only the edges between vertices in $S$. Let $L$ be the Laplacian matrix of $G$ and let $L_S$ be the Laplacian of $G_S$. A set of vertices $S$ is $\\epsilon$-light if the matrix $\\epsilon L - L_S$ is positive semidefinite. Does there exist a constant $c > 0$ so that for every graph $G$ and every $\\epsilon$ between $0$ and $1$, $V$ contains an $\\epsilon$-light subset $S$ of size at least $c\\epsilon |V|$?',
      },
    ],
  },
  reviewing: {
    zh: [
      '**定理**：设 $G$ 是有限群，$H$ 是 $G$ 的子群，则 $|H|$ 整除 $|G|$。\n\n**证明**：考虑 $G$ 关于 $H$ 的左陪集分解。对任意 $g \\in G$，定义左陪集 $gH = \\{gh \\mid h \\in H\\}$。\n\n首先，$gH$ 与 $H$ 等势，因为映射 $h \\mapsto gh$ 是双射。\n\n其次，两个左陪集 $g_1H$ 和 $g_2H$ 要么相等，要么不交。证明：若 $g_1H \\cap g_2H \\neq \\emptyset$，取 $x \\in g_1H \\cap g_2H$，则 $x = g_1h_1 = g_2h_2$，得 $g_1 = g_2h_2h_1^{-1} \\in g_2H$，故 $g_1H \\subseteq g_2H$。对称地 $g_2H \\subseteq g_1H$，因此 $g_1H = g_2H$。\n\n因此 $G$ 被划分为若干两两不交的左陪集，设有 $k$ 个陪集，则 $|G| = k|H|$，即 $|H|$ 整除 $|G|$。$\\square$',
      '**定理**：$n$ 阶方阵的行列式等于其特征值之积。\n\n**证明**：设 $A$ 是 $n$ 阶复方阵，特征值为 $\\lambda_1, \\ldots, \\lambda_n$（重根按重数计）。\n\n在复数域上，$A$ 相似于 Jordan 标准型 $J$，即存在可逆矩阵 $P$ 使得 $A = PJP^{-1}$。\n\n由行列式的相似不变性：$\\det(A) = \\det(PJP^{-1}) = \\det(P)\\det(J)\\det(P^{-1}) = \\det(J)$。\n\nJordan 标准型 $J$ 是分块对角矩阵，每个 Jordan 块对应一个特征值。$J$ 是上三角矩阵，其行列式等于主对角线元素之积，即 $\\det(J) = \\lambda_1 \\cdots \\lambda_n$。\n\n因此 $\\det(A) = \\lambda_1 \\cdots \\lambda_n$。$\\square$',
      '**定理**：素数有无穷多个。\n\n**证明**（欧几里得）：假设素数只有有限个，记为 $p_1, p_2, \\ldots, p_n$。\n\n考察数 $N = p_1 p_2 \\cdots p_n + 1$。\n\n由于 $N > 1$，根据算术基本定理，$N$ 可分解为素因数之积。设 $p$ 是 $N$ 的某个素因数。\n\n若 $p$ 是 $p_1, \\ldots, p_n$ 中的某个，不妨设 $p = p_i$，则 $p \\mid p_1 \\cdots p_n$ 且 $p \\mid N$，故 $p \\mid (N - p_1 \\cdots p_n) = 1$，矛盾。\n\n因此 $p$ 不在 $\\{p_1, \\ldots, p_n\\}$ 中，这与"所有素数为 $p_1, \\ldots, p_n$"矛盾。\n\n故素数有无穷多个。$\\square$',
    ],
    en: [
      '**Theorem**: Let $G$ be a finite group and $H$ a subgroup. Then $|H|$ divides $|G|$.\n\n**Proof**: Consider the partition of $G$ into left cosets of $H$. For any $g \\in G$, define $gH = \\{gh \\mid h \\in H\\}$.\n\nFirst, $|gH| = |H|$ since the map $h \\mapsto gh$ is a bijection.\n\nSecond, two cosets $g_1H$ and $g_2H$ are either equal or disjoint. Proof: if $g_1H \\cap g_2H \\neq \\emptyset$, take $x = g_1h_1 = g_2h_2$, then $g_1 = g_2h_2h_1^{-1} \\in g_2H$, so $g_1H \\subseteq g_2H$. By symmetry $g_2H \\subseteq g_1H$, hence $g_1H = g_2H$.\n\nThus $G$ is partitioned into $k$ disjoint cosets, so $|G| = k|H|$, i.e., $|H|$ divides $|G|$. $\\square$',
      '**Theorem**: The determinant of an $n \\times n$ matrix equals the product of its eigenvalues.\n\n**Proof**: Let $A$ be an $n \\times n$ complex matrix with eigenvalues $\\lambda_1, \\ldots, \\lambda_n$ (counted with multiplicity).\n\nOver $\\mathbb{C}$, $A$ is similar to its Jordan normal form $J$: there exists invertible $P$ such that $A = PJP^{-1}$.\n\nBy similarity invariance: $\\det(A) = \\det(PJP^{-1}) = \\det(P)\\det(J)\\det(P^{-1}) = \\det(J)$.\n\nJordan form $J$ is block diagonal with each Jordan block corresponding to an eigenvalue. $J$ is upper triangular, so $\\det(J) = \\lambda_1 \\cdots \\lambda_n$.\n\nTherefore $\\det(A) = \\lambda_1 \\cdots \\lambda_n$. $\\square$',
      '**Theorem**: There are infinitely many primes.\n\n**Proof** (Euclid): Suppose there are only finitely many primes $p_1, p_2, \\ldots, p_n$.\n\nConsider $N = p_1 p_2 \\cdots p_n + 1$.\n\nSince $N > 1$, by the fundamental theorem of arithmetic, $N$ has a prime divisor $p$.\n\nIf $p \\in \\{p_1, \\ldots, p_n\\}$, say $p = p_i$, then $p \\mid p_1 \\cdots p_n$ and $p \\mid N$, so $p \\mid (N - p_1 \\cdots p_n) = 1$, contradiction.\n\nThus $p \\notin \\{p_1, \\ldots, p_n\\}$, contradicting our assumption that all primes are $p_1, \\ldots, p_n$.\n\nTherefore there are infinitely many primes. $\\square$',
    ],
  },
  searching: {
    zh: [
      'Cauchy 序列收敛定理',
      '有限群 Lagrange 定理',
      '连续函数中间值定理 Lean 4',
    ],
    en: [
      'Cauchy sequence convergence',
      'Lagrange theorem finite group',
      'intermediate value theorem continuous function',
    ],
  },
};

function getNestedI18n(obj, path) {
  if (!path) return '';
  return path.split('.').reduce((o, k) => (o && o[k] !== undefined ? o[k] : null), obj) ?? path;
}

function t(key, vars) {
  let str = getNestedI18n(I18N[AppState.lang], key);
  if (typeof str !== 'string') return key;
  if (vars) {
    Object.entries(vars).forEach(([k, v]) => { str = str.replace(`{${k}}`, v); });
  }
  return str;
}

let _i18nNodes = null;
function getI18nNodes() {
  if (!_i18nNodes) _i18nNodes = Array.from(document.querySelectorAll('[data-i18n]'));
  return _i18nNodes;
}

function detectLang() {
  const saved = localStorage.getItem('vp_lang');
  if (saved && (saved === 'zh' || saved === 'en')) return saved;
  return 'en';
}

function applyLang(lang) {
  if (!I18N[lang]) return;
  AppState.lang = lang;
  localStorage.setItem('vp_lang', lang);
  document.documentElement.setAttribute('lang', lang === 'zh' ? 'zh-CN' : 'en');

  getI18nNodes().forEach(el => {
    const str = getNestedI18n(I18N[lang], el.dataset.i18n);
    if (str && str !== el.dataset.i18n) el.textContent = str;
  });

  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    el.placeholder = getNestedI18n(I18N[lang], el.dataset.i18nPlaceholder) || el.placeholder;
  });
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    const v = getNestedI18n(I18N[lang], el.dataset.i18nTitle);
    if (v) el.title = v;
  });
  document.querySelectorAll('[data-i18n-aria-label]').forEach(el => {
    const v = getNestedI18n(I18N[lang], el.dataset.i18nAriaLabel);
    if (v) el.setAttribute('aria-label', v);
  });
  document.querySelectorAll('[data-i18n-tooltip]').forEach(el => {
    const v = getNestedI18n(I18N[lang], el.dataset.i18nTooltip);
    if (v) el.setAttribute('data-tooltip', v);
  });

  document.querySelectorAll('.lang-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.lang === lang);
  });
  // plan F.3 (T51)：分段切换器同步
  if (typeof window.__syncLangSeg === 'function') window.__syncLangSeg();
  _syncLangTopbar();

  _syncModeChipLabel();
  _syncModeTabs();
  renderExamplePrompts();
  refreshHistorySidebar();
  _renderDocsModal(lang);

  // 切换语言时同步模型下拉的能力标签
  document.querySelectorAll('#model-dropdown .chip-option[data-tier-zh]').forEach(li => {
    const tierEl = li.querySelector('.chip-tier');
    if (tierEl) tierEl.textContent = lang === 'zh' ? li.dataset.tierZh : li.dataset.tierEn;
  });

  // 若提示条正在显示，立即切换为新语言内容
  const tipEl = document.getElementById('wait-tip-bar');
  if (tipEl) {
    const tips = _WAIT_TIPS[lang] || _WAIT_TIPS.en;
    const txtEl = tipEl.querySelector('.wait-tip-text');
    if (txtEl) {
      tipEl.classList.remove('visible');
      setTimeout(() => {
        txtEl.innerHTML = _renderMathText(tips[_waitTipIdx % tips.length]);
        tipEl.classList.add('visible');
        renderKatexFallback(tipEl);
      }, 400);
    }
  }
}

function _initModelInfoCard() {
  const card = document.getElementById('model-info-card');
  const dropdown = document.getElementById('model-dropdown');
  if (!card || !dropdown) return;

  let _hideTimer = null;

  const show = (li) => {
    if (_hideTimer) { clearTimeout(_hideTimer); _hideTimer = null; }
    const lang = AppState.lang || 'zh';
    const name  = li.querySelector('.chip-opt-name')?.textContent?.trim() || '';
    const tier  = lang === 'zh' ? (li.dataset.tierZh || '') : (li.dataset.tierEn || '');
    const desc  = lang === 'zh' ? (li.dataset.descZh || '') : (li.dataset.descEn || '');
    const note  = lang === 'zh' ? (li.dataset.noteZh || '') : (li.dataset.noteEn || '');

    if (!desc) return;

    card.querySelector('.mic-name').textContent = name;
    card.querySelector('.mic-tier-badge').textContent = tier;
    card.querySelector('.mic-desc').textContent = desc;
    const noteEl = card.querySelector('.mic-note');
    noteEl.textContent = note;
    noteEl.style.display = note ? '' : 'none';

    // 定位：紧贴 dropdown 左侧，垂直对齐悬停行
    const liRect = li.getBoundingClientRect();
    const dropRect = dropdown.getBoundingClientRect();
    const cardW = 238;
    const left = dropRect.left - cardW - 8;
    let top = liRect.top;
    // 防止卡片超出视口底部
    const cardH = 130;
    if (top + cardH > window.innerHeight - 8) {
      top = window.innerHeight - cardH - 8;
    }
    card.style.left = Math.max(8, left) + 'px';
    card.style.top  = top + 'px';
    card.classList.add('visible');
  };

  const hide = (delay = 80) => {
    _hideTimer = setTimeout(() => { card.classList.remove('visible'); }, delay);
  };

  dropdown.querySelectorAll('.chip-option').forEach(li => {
    li.addEventListener('mouseenter', () => show(li));
    li.addEventListener('mouseleave', () => hide());
  });
  // 鼠标离开整个下拉时隐藏
  dropdown.addEventListener('mouseleave', () => hide(50));
}

function _renderDocsModal(lang) {
  const body = document.getElementById('docs-body');
  if (!body) return;
  const d = (I18N[lang] || I18N.zh).docs;
  if (!d) return;
  const cards = (d.cards || []).map(c =>
    `<div class="docs-card"><div class="docs-card-icon">${c.icon}</div><div class="docs-card-title">${c.title}</div><div class="docs-card-body">${c.body}</div></div>`
  ).join('');
  const steps = (d.steps || []).map(s =>
    `<div class="docs-step"><span class="docs-step-num">${s.n}</span><div><strong>${s.title}</strong>：${s.body}</div></div>`
  ).join('');
  const tipLabel = lang === 'zh' ? '提示' : 'Tip';
  body.innerHTML =
    `<div class="docs-hero"><h2>vibe_proving</h2><p>${d.heroPara}</p></div>` +
    `<div class="docs-section"><h3>${d.modulesTitle}</h3><div class="docs-grid">${cards}</div></div>` +
    `<div class="docs-section"><h3>${d.kbTitle}</h3><p>${d.kbDesc}</p><div class="docs-steps">${steps}</div></div>` +
    `<div class="docs-section docs-tip"><strong>${tipLabel}：</strong>${d.tip}</div>`;
}

/* ─────────────────────────────────────────────────────────────
   2. 主题（深/浅）
───────────────────────────────────────────────────────────── */
function detectTheme() {
  const saved = localStorage.getItem('vp_theme');
  if (saved) return saved;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('vp_theme', theme);

  const lightLink = document.getElementById('hljs-theme-light');
  const darkLink  = document.getElementById('hljs-theme-dark');
  if (lightLink) lightLink.disabled = (theme === 'dark');
  if (darkLink)  darkLink.disabled  = (theme !== 'dark');

  const btn = document.getElementById('btn-theme');
  if (btn) btn.textContent = theme === 'dark' ? '☾' : '☀';
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'light';
  applyTheme(current === 'dark' ? 'light' : 'dark');
}

/* ─────────────────────────────────────────────────────────────
   3. Toast
───────────────────────────────────────────────────────────── */
function showToast(type, message, duration = 3500) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const icons = { error: '✕', success: '✓', info: 'ℹ', warning: '!' };
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.setAttribute('role', type === 'error' ? 'alert' : 'status');
  toast.innerHTML = `
    <span class="toast-icon">${icons[type] || 'ℹ'}</span>
    <span class="toast-msg">${escapeHtml(message)}</span>
    <button class="toast-close" aria-label="close">×</button>
  `;
  container.appendChild(toast);

  // 进场动画下一帧触发
  requestAnimationFrame(() => toast.classList.add('toast-enter'));

  const remove = () => {
    toast.classList.remove('toast-enter');
    toast.classList.add('toast-leave');
    setTimeout(() => toast.remove(), 320);
  };
  toast.querySelector('.toast-close').addEventListener('click', remove);

  if (duration > 0) setTimeout(remove, duration);
}

/* ─────────────────────────────────────────────────────────────
   4. 渲染引擎（marked + KaTeX + highlight.js）
───────────────────────────────────────────────────────────── */
function escapeHtml(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function initRenderer() {
  if (typeof hljs !== 'undefined') {
    if (typeof hljs.registerLanguage === 'function' && hljs.getLanguage && !hljs.getLanguage('lean')) {
      try {
        hljs.registerLanguage('lean', () => ({
          keywords: {
            keyword: 'theorem lemma def let fun by exact apply intro cases induction simp rfl have show suffices use',
            built_in: 'Nat Int Real Complex List Finset Set Prop Type',
          },
          contains: [
            { className: 'comment', begin: '--', end: '$' },
            { className: 'string', begin: '"', end: '"' },
            { className: 'number', begin: '\\b\\d+(\\.\\d+)?\\b' },
          ],
        }));
      } catch {}
    }
  }

  if (typeof markedHighlight !== 'undefined' && typeof hljs !== 'undefined') {
    const ext = window.markedHighlight?.markedHighlight || window.markedHighlight;
    if (typeof ext === 'function') {
      marked.use(ext({
        langPrefix: 'hljs language-',
        highlight(code, lang) {
          const language = hljs.getLanguage(lang) ? lang : 'plaintext';
          try { return hljs.highlight(code, { language }).value; } catch { return escapeHtml(code); }
        }
      }));
    }
  }

  if (typeof markedKatex !== 'undefined') {
    marked.use(markedKatex({
      throwOnError: false,
      output: 'html',
      // 允许 $...$ 中包含单个字母（如 $p$、$M$），不要求非空且多字符
      nonStandard: true,
    }));
  }

  // 自定义 renderer：代码块加复制按钮（兼容 marked 4.x 老 API）
  const renderer = new marked.Renderer();
  const originalCode = renderer.code.bind(renderer);
  renderer.code = function(code, lang, escaped) {
    const inner = originalCode(code, lang, escaped);
    return `<div class="code-block-wrapper">
      <button class="code-copy-btn" onclick="copyCodeBlock(this)">${t('ui.copy')}</button>
      ${inner}
    </div>`;
  };

  marked.use({ renderer });
  marked.setOptions({ breaks: true, gfm: true });
}

/**
 * 自动包裹「明显是数学」但 LLM 漏写 $...$ 的片段。
 * 只匹配高置信度模式，避免误伤散文：
 *   1. 含 LaTeX 命令的（\\frac、\\sqrt、\\sum、\\int、\\mathbb 等）
 *   2. 含数学专属符号（≤、≥、≠、∈、∀、∃、→、↦、⊂、⊆、∪、∩、π、α、β、γ、∞）
 *   3. 形如 "var = expr" 且 expr 含 +/*-/^ 的（如 a = 2m+1, f(x)=x^2）
 * 跳过：代码块、行内 code、已经被 $...$ 包裹的、URL。
 */
/**
 * plan D：sanitizeLatex —— 修复 LLM 常见 LaTeX 笔误，让 KaTeX 不至于因小错而整段 fallback。
 * 在 autoWrapMath 之前调用，仅对"显式数学块"（$...$ 或 $$...$$）内部生效，
 * 不动明文。
 */
// plan F.3 (T55)：把 Unicode 上标/下标字符（²³、ₙ 等）转回 ASCII `^N`/`_N`，
// 这样 autoWrapMath 才能识别 `a² + b² = c²` 这类裸数学式并交给 KaTeX。
const _SUPER_MAP = { '⁰':'0','¹':'1','²':'2','³':'3','⁴':'4','⁵':'5','⁶':'6','⁷':'7','⁸':'8','⁹':'9','⁺':'+','⁻':'-','⁼':'=','⁽':'(','⁾':')','ⁿ':'n','ⁱ':'i' };
const _SUB_MAP   = { '₀':'0','₁':'1','₂':'2','₃':'3','₄':'4','₅':'5','₆':'6','₇':'7','₈':'8','₉':'9','₊':'+','₋':'-','₌':'=','₍':'(','₎':')','ₙ':'n','ᵢ':'i' };

// Mathematical Italic / Bold / 等 Unicode 数学字母 → ASCII。LLM 经常吐出这种"伪渲染"。
function _normalizeMathItalicLetters(text) {
  return text.replace(/[\uD835][\uDC00-\uDFFF]/g, (m) => {
    const cp = m.codePointAt(0);
    // U+1D400..U+1D419 Mathematical Bold Capital A..Z
    if (cp >= 0x1D400 && cp <= 0x1D419) return String.fromCharCode(0x41 + cp - 0x1D400);
    if (cp >= 0x1D41A && cp <= 0x1D433) return String.fromCharCode(0x61 + cp - 0x1D41A);
    // U+1D434..U+1D44D Mathematical Italic Capital A..Z
    if (cp >= 0x1D434 && cp <= 0x1D44D) return String.fromCharCode(0x41 + cp - 0x1D434);
    // U+1D44E..U+1D467 Mathematical Italic Small a..z
    if (cp >= 0x1D44E && cp <= 0x1D467) return String.fromCharCode(0x61 + cp - 0x1D44E);
    // Mathematical Bold Italic
    if (cp >= 0x1D468 && cp <= 0x1D481) return String.fromCharCode(0x41 + cp - 0x1D468);
    if (cp >= 0x1D482 && cp <= 0x1D49B) return String.fromCharCode(0x61 + cp - 0x1D482);
    // Script
    if (cp >= 0x1D49C && cp <= 0x1D4B5) return String.fromCharCode(0x41 + cp - 0x1D49C);
    if (cp >= 0x1D4B6 && cp <= 0x1D4CF) return String.fromCharCode(0x61 + cp - 0x1D4B6);
    // Mathematical Bold Italic + variants — 先粗略覆盖
    if (cp >= 0x1D5A0 && cp <= 0x1D5B9) return String.fromCharCode(0x41 + cp - 0x1D5A0); // Sans-Serif Bold Cap
    if (cp >= 0x1D5BA && cp <= 0x1D5D3) return String.fromCharCode(0x61 + cp - 0x1D5BA);
    // 数字 0-9 (Mathematical Bold Digits / etc.)
    if (cp >= 0x1D7CE && cp <= 0x1D7D7) return String.fromCharCode(0x30 + cp - 0x1D7CE);
    if (cp >= 0x1D7D8 && cp <= 0x1D7E1) return String.fromCharCode(0x30 + cp - 0x1D7D8);
    if (cp >= 0x1D7E2 && cp <= 0x1D7EB) return String.fromCharCode(0x30 + cp - 0x1D7E2);
    if (cp >= 0x1D7EC && cp <= 0x1D7F5) return String.fromCharCode(0x30 + cp - 0x1D7EC);
    if (cp >= 0x1D7F6 && cp <= 0x1D7FF) return String.fromCharCode(0x30 + cp - 0x1D7F6);
    return m;
  })
  // 单独的 ℎ U+210E (Planck) → h
  .replace(/[\u210E]/g, 'h')
  // ℝ ℕ ℤ ℚ ℂ → R N Z Q C （留给 autoWrapMath 识别后会包成 $\mathbb{R}$ 也行）
  .replace(/[\u211D]/g, 'R').replace(/[\u2115]/g, 'N').replace(/[\u2124]/g, 'Z')
  .replace(/[\u211A]/g, 'Q').replace(/[\u2102]/g, 'C');
}

// plan F.3 (T55)：LLM 经常把公式拆成"每个 token 一行"竖排：
//   `\na\n2\n+\nb\n2\n=\nc\n2\n` → `a 2 + b 2 = c 2` 单行
// 检测条件：连续 ≥ 3 行，每行只含 1-3 个 ASCII 数学/字母 token。
function _collapseVerticalMath(text) {
  if (!text) return text;
  const lines = text.split('\n');
  const isMathToken = (s) => /^[A-Za-z0-9+\-*/=^_(){}\[\]\\]{1,4}$/.test(s.trim());
  const out = [];
  let i = 0;
  while (i < lines.length) {
    let j = i;
    while (j < lines.length && isMathToken(lines[j])) j++;
    if (j - i >= 3) {
      // 折叠 i..j-1，并尝试还原 `letter <NL> digit` → `letter^digit`
      let merged = lines.slice(i, j).map(s => s.trim()).join(' ');
      // 字母 / `)` / `}` 后空格紧跟数字 → 上标
      merged = merged.replace(/([A-Za-z\)\}])\s+(\d+)/g, '$1^$2');
      // 去除运算符两侧的多余空格
      merged = merged.replace(/\s*([+\-*/=])\s*/g, ' $1 ').replace(/\s{2,}/g, ' ');
      out.push(merged);
      i = j;
    } else {
      out.push(lines[i]);
      i++;
    }
  }
  return out.join('\n');
}

function _normalizeUnicodeSubSup(text) {
  if (!text) return text;
  // 0) 先把 Mathematical Italic 字符转回 ASCII（𝑎𝑏𝑐 → abc）
  text = _normalizeMathItalicLetters(text);
  // 0.5) 折叠竖排数学
  text = _collapseVerticalMath(text);
  // 把连续的 Unicode 上标 ²³ 折叠成 ^{23}；单个 ² 转 ^2
  return text
    .replace(/([⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱ]+)/g, (m) => {
      const ascii = [...m].map(ch => _SUPER_MAP[ch] || ch).join('');
      return ascii.length === 1 ? `^${ascii}` : `^{${ascii}}`;
    })
    .replace(/([₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₙᵢ]+)/g, (m) => {
      const ascii = [...m].map(ch => _SUB_MAP[ch] || ch).join('');
      return ascii.length === 1 ? `_${ascii}` : `_{${ascii}}`;
    });
}

function sanitizeLatex(text) {
  if (!text) return text;
  // 0) Unicode 上下标归一化
  text = _normalizeUnicodeSubSup(text);
  // 1) 修 `$...$` / `$$...$$` 内部的 `\cmd{X}{sub}` → `\cmd{X}_{sub}`
  //    LLM 常把下标漏写为第二个 `{...}`（如 `\mathcal{C}{cf}`、`\mathbb{R}{n}`），
  //    KaTeX 会把第二个 {} 当作错误的额外参数。仅在 \mathcal/\mathbb/\mathfrak 这类
  //    "单参数命令" 后才修复，避免误伤 \frac 等多参数命令。
  const fix = (mathStr) => {
    return mathStr.replace(
      /(\\(?:mathcal|mathbb|mathfrak|mathrm|mathbf|mathit|mathsf|mathtt|operatorname)\{[^{}]+\})\{([^{}]+)\}/g,
      '$1_{$2}'
    );
  };
  let s = text;
  // $$...$$
  s = s.replace(/\$\$([\s\S]*?)\$\$/g, (m, inner) => `$$${fix(inner)}$$`);
  // $...$（单行）
  s = s.replace(/\$([^\n$]+?)\$/g, (m, inner) => `$${fix(inner)}$`);

  // 2) 末尾落单 `$`：奇数个 `$` 会让 KaTeX 把整个段落当成 inline math。
  //    若全文 `$` 数量为奇数且最后一个无对应闭合，自动补齐。
  const dollarMatches = (s.match(/\$/g) || []).length;
  // 仅当 $ 总数为奇数（成对 $$ 视为 2 个）才补；保守仅在末尾追加
  if (dollarMatches % 2 === 1 && !/\$\s*$/.test(s)) {
    // 不主动补齐（避免错误吞掉行内文字），仅打日志（dev only）
    // s += '$';
  }

  // 3) 把 `\$` 误转义为字面 $（一些模型会在 LaTeX 区里多打 \）
  //    仅替换在 $...$ 之外的；这里简化：保留行为，留给 marked 处理
  return s;
}

// plan F.3 (T55)：扫描 \frac{...}{...}、\sqrt{...}、\mathcal{...}_{...} 这类
// 含嵌套大括号的 LaTeX 命令，把整段（含所有连续参数）用 $...$ 包裹。
const _LATEX_NESTED_CMDS = new Set([
  'frac','sqrt','sum','prod','int','oint','iint','iiint','lim','sup','inf',
  'mathbb','mathcal','mathfrak','mathrm','mathbf','mathit','mathsf','mathtt',
  'operatorname','overline','underline','overbrace','underbrace','widehat','widetilde',
  'hat','bar','tilde','vec','dot','ddot','prime','left','right',
  'binom','dfrac','tfrac','choose','overset','underset','stackrel'
]);
function _wrapLatexCommandsWithNestedBraces(text) {
  if (!text || text.indexOf('\\') < 0) return text;
  let out = '';
  let i = 0;
  while (i < text.length) {
    const ch = text[i];
    if (ch !== '\\') { out += ch; i++; continue; }
    // 已经在 $...$ 内？查左边最近的未闭合 $
    // 简化：让外层 placeholder 已经把 $...$ 抠掉，所以这里看到的 \cmd 一定在明文区
    const m = text.slice(i).match(/^\\([A-Za-z]+)/);
    if (!m) { out += ch; i++; continue; }
    const cmd = m[1];
    if (!_LATEX_NESTED_CMDS.has(cmd)) { out += ch; i++; continue; }
    // 起点 j = \cmd 末尾
    let j = i + 1 + cmd.length;
    // 吞掉紧跟的所有 {...} 参数（可嵌套）
    let consumedAny = false;
    while (j < text.length && (text[j] === '{' || text[j] === '_' || text[j] === '^')) {
      if (text[j] === '_' || text[j] === '^') {
        j++;
        if (j < text.length && text[j] === '{') {
          const end = _matchBrace(text, j);
          if (end < 0) break;
          j = end + 1;
        } else if (j < text.length && /[A-Za-z0-9Ͱ-Ͽ]/.test(text[j])) {
          j++;
        } else { break; }
        consumedAny = true;
      } else {
        const end = _matchBrace(text, j);
        if (end < 0) break;
        j = end + 1;
        consumedAny = true;
      }
    }
    const piece = text.slice(i, j);
    out += `$${piece}$`;
    i = j;
  }
  return out;
}
function _matchBrace(s, openIdx) {
  if (s[openIdx] !== '{') return -1;
  let depth = 0;
  for (let k = openIdx; k < s.length; k++) {
    const c = s[k];
    if (c === '\\') { k++; continue; }
    if (c === '{') depth++;
    else if (c === '}') { depth--; if (depth === 0) return k; }
  }
  return -1;
}

function autoWrapMath(text) {
  if (!text) return text;
  // plan D：先 sanitize 已有数学块，再做包裹
  text = sanitizeLatex(text);
  // 切出 ``` 代码块和 `…` 行内 code，原样保留
  const placeholders = [];
  const protect = (s, re) => s.replace(re, m => {
    placeholders.push(m);
    return `\u0000${placeholders.length - 1}\u0000`;
  });
  let s = text;
  s = protect(s, /```[\s\S]*?```/g);
  s = protect(s, /`[^`\n]+`/g);
  s = protect(s, /\$\$[\s\S]*?\$\$/g);
  s = protect(s, /\$[^$\n]+\$/g);
  s = protect(s, /\\\([\s\S]*?\\\)/g);
  s = protect(s, /\\\[[\s\S]*?\\\]/g);
  s = protect(s, /https?:\/\/\S+/g);

  // 1) LaTeX 命令片段：\\command{...} 或 \\command（前后非字母数字时）
  // 1a) plan F.3 (T55)：含嵌套大括号的 LaTeX 命令（`\frac{a}{b+\sqrt{c}}` 等），
  //     用手工 brace matching 找完整片段后再包 $...$。
  s = _wrapLatexCommandsWithNestedBraces(s);
  // Merge adjacent $...$ inline blocks (e.g. "$\frac{a}{b}$$\oint_\gamma$" → one block)
  // to prevent accidental "$$" which KaTeX interprets as display math delimiters.
  { let _pv; do { _pv = s; s = s.replace(/\$([^$\n]+)\$\$([^$\n]+)\$/g, (_, a, b) => '$' + a + b + '$'); } while (s !== _pv); }
  // 立即把刚生成的 $...$ 也加入保护，避免后续 rule 4/5 在 \frac 内部嵌套 $
  s = protect(s, /\$[^$\n]+\$/g);

  // 1b) 兜底：纯 `\cmd` 无参形式（如 \alpha、\cdot、\to）
  s = s.replace(/(?<![\\$\w])(\\(?:frac|sqrt|sum|prod|int|lim|sup|inf|mathbb|mathcal|mathfrak|mathrm|mathbf|mathit|operatorname|forall|exists|in|notin|subset|subseteq|cup|cap|leq|geq|neq|to|mapsto|Rightarrow|Leftrightarrow|alpha|beta|gamma|delta|epsilon|varepsilon|zeta|eta|theta|vartheta|iota|kappa|lambda|mu|nu|xi|pi|rho|sigma|tau|upsilon|phi|varphi|chi|psi|omega|Gamma|Delta|Theta|Lambda|Xi|Pi|Sigma|Phi|Psi|Omega|infty|partial|nabla|cdot|cdots|ldots|times|div|pm|mp|approx|equiv|sim|propto|circ|prime)(?:\{[^{}]*\}|\b))/g,
    '$$$1$$');

  // 2) 含数学符号的小段（限定 ≤30 字符，避免吞掉整句）
  s = s.replace(/([A-Za-z0-9_()\s.,]*[≤≥≠∈∉∀∃⊂⊆∪∩πφψθαβγδλμω∞→↦≡≅∧∨][^\n。.;]{0,30})/g,
    (m) => {
      // 已含 $ 跳过
      if (m.includes('$')) return m;
      // 必须有数学符号
      if (!/[≤≥≠∈∉∀∃⊂⊆∪∩πφψθαβγδλμω∞→↦≡≅∧∨]/.test(m)) return m;
      const trimmed = m.trim();
      const lead = m.match(/^\s*/)[0];
      const tail = m.match(/\s*$/)[0];
      return `${lead}$${trimmed}$${tail}`;
    });

  // 3) "var = expr"（左 1-3 字符标识符，右含 +/-/*/^/数字）— 仅当行内独立段
  s = s.replace(/(^|[\s(])([A-Za-z][A-Za-z0-9_']{0,3}\s*=\s*[A-Za-z0-9_+\-*/^()\\\s]{1,40})(?=[\s,;.)。，；]|$)/gm,
    (full, pre, expr) => {
      if (expr.includes('$')) return full;
      // 必须含运算符或上标，避免吞 "x = hello"
      if (!/[+\-*/^]|\d/.test(expr)) return full;
      // 不要包裹 markdown 列表/标题前缀
      if (/^[#\->*]/.test(expr.trim())) return full;
      return `${pre}$${expr.trim()}$`;
    });

  // 4) plan F.3 (T55)：含 ^ 上标的方程式 — 形如 a^2 + b^2 = c^2、x^n - y^n
  //    pre 允许中文字符（中文段落里 `c^2 = a^2 + b^2`），用否定式：非数学字符
  s = s.replace(/(^|[^A-Za-z0-9_$\\^])([A-Za-z]\^[0-9A-Za-z]+(?:\s*[+\-*/=]\s*[A-Za-z0-9]+\^?[0-9A-Za-z]*){1,6})(?=[^A-Za-z0-9_$\\^]|$)/g,
    (full, pre, expr) => {
      if (expr.includes('$')) return full;
      return `${pre}$${expr.trim()}$`;
    });

  // 把规则 4 产生的新 $...$ 也加入 placeholder 保护，避免规则 5 误嵌套
  s = protect(s, /\$[^$\n]+\$/g);

  // 5) plan F.3 (T55) 加强：兜底含 ^ 上标的小片段 — 形如 c^2、(a+b)^2、x^{n+1}
  //    pre 用否定式（非字母数字下划线/$），覆盖中文段落 "一种是(a+b)^2，..."
  s = s.replace(/(^|[^A-Za-z0-9_$\\])((?:[A-Za-z0-9]|\([A-Za-z0-9+\-*/\s]{1,12}\))\^(?:[A-Za-z0-9]|\{[A-Za-z0-9+\-*/\s,]{1,12}\}))(?=[^A-Za-z0-9_$\\^]|$)/g,
    (full, pre, expr) => {
      if (expr.includes('$')) return full;
      return `${pre}$${expr.trim()}$`;
    });

  // 还原 placeholders
  s = s.replace(/\u0000(\d+)\u0000/g, (_, i) => placeholders[+i] || '');
  return s;
}

/* plan M.3：分段缓存的增量 Markdown 渲染
 *   - 把 text 按 \n\n 切成段落
 *   - 已完成段（不是最后一段）走缓存，永不重新 parse
 *   - 仅最后一段（流式中的"未完成段"）每次重 parse
 *   - LRU 上限 200 段，防内存膨胀
 */
const _MD_CACHE = new Map();
const _MD_CACHE_MAX = 200;

function _renderOneSegment(seg) {
  if (!seg) return '';
  if (_MD_CACHE.has(seg)) return _MD_CACHE.get(seg);
  let html;
  try {
    html = marked.parse(autoWrapMath(seg));
  } catch {
    html = `<pre>${escapeHtml(seg)}</pre>`;
  }
  if (_MD_CACHE.size >= _MD_CACHE_MAX) {
    const firstKey = _MD_CACHE.keys().next().value;
    _MD_CACHE.delete(firstKey);
  }
  _MD_CACHE.set(seg, html);
  return html;
}

function renderMarkdown(text) {
  if (!text) return '';
  // 完整 markdown：直接 parse 并缓存（用于 finish 阶段）
  return _renderOneSegment(text);
}

/** 流式 Markdown：把 text 按 \n\n 切段，已完成段走缓存，只重做最后一段。 */
function renderStreamingMarkdown(text) {
  if (!text) return '';
  // 段落切分：保留分隔符以便拼回
  const parts = text.split(/(\n\n)/);
  // 把每个非分隔段做单段缓存渲染；分隔符直接保留
  let out = '';
  for (let i = 0; i < parts.length; i++) {
    const p = parts[i];
    if (p === '\n\n') { out += ''; continue; }
    // 最后一段如果尚未跟一个 \n\n（即还在打字），不缓存
    const isTrailing = (i === parts.length - 1) && !text.endsWith('\n\n');
    if (isTrailing) {
      try {
        out += marked.parse(autoWrapMath(p));
      } catch {
        out += `<pre>${escapeHtml(p)}</pre>`;
      }
    } else {
      out += _renderOneSegment(p);
    }
  }
  return out;
}

/** plan D：KaTeX 兜底。出错时不再显示裸 $...$，改用等宽样式提示。 */
function renderKatexFallback(rootEl) {
  if (!rootEl || typeof renderMathInElement === 'undefined') return;
  try {
    renderMathInElement(rootEl, {
      delimiters: [
        { left: '$$', right: '$$', display: true },
        { left: '$',  right: '$',  display: false },
        { left: '\\[', right: '\\]', display: true },
        { left: '\\(', right: '\\)', display: false },
      ],
      throwOnError: false,
      errorColor: '#b00020',
      // plan D：错误回调返回美化的等宽 fallback，而非裸 `$expr$`
      errorCallback: (msg, err) => {
        // 只 console.warn，不弹窗；视觉 fallback 由 KaTeX 默认 errorColor 处理
        if (window.console && console.warn) console.warn('[katex]', msg);
      },
      ignoredTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code'],
    });
    // 二次扫描：若仍存在裸 `$xxx$` 文本节点（KaTeX 没识别出来），用等宽样式包裹
    _wrapBareDollarText(rootEl);
  } catch (e) {
    if (window.console && console.warn) console.warn('[katex]', e);
  }
}

/** plan D：把仍然裸露的 $...$ 文本片段降级为等宽 code，不在前端显示原始字符。 */
function _wrapBareDollarText(rootEl) {
  if (!rootEl) return;
  const walker = document.createTreeWalker(rootEl, NodeFilter.SHOW_TEXT, {
    acceptNode: (n) => {
      if (!n.nodeValue || !/\$[^$\n]+\$/.test(n.nodeValue)) return NodeFilter.FILTER_REJECT;
      // 跳过 code/pre/script/style/.katex 内部
      let p = n.parentNode;
      while (p && p !== rootEl) {
        const tag = (p.tagName || '').toLowerCase();
        if (tag === 'code' || tag === 'pre' || tag === 'script' || tag === 'style') return NodeFilter.FILTER_REJECT;
        if (p.classList && (p.classList.contains('katex') || p.classList.contains('katex-display'))) return NodeFilter.FILTER_REJECT;
        p = p.parentNode;
      }
      return NodeFilter.FILTER_ACCEPT;
    }
  });
  const targets = [];
  let cur;
  while ((cur = walker.nextNode())) targets.push(cur);
  for (const node of targets) {
    const html = node.nodeValue.replace(
      /\$([^$\n]+)\$/g,
      (m, expr) => `<code class="latex-fallback" title="LaTeX 解析失败">${escapeHtml(expr)}</code>`
    );
    if (html === node.nodeValue) continue;
    const span = document.createElement('span');
    span.innerHTML = html;
    node.replaceWith(...span.childNodes);
  }
}

window.copyCodeBlock = function(btn) {
  const pre = btn.closest('.code-block-wrapper')?.querySelector('pre');
  if (!pre) return;
  const text = pre.innerText || pre.textContent || '';
  navigator.clipboard.writeText(text).then(() => {
    btn.textContent = t('ui.copied');
    btn.classList.add('copied');
    setTimeout(() => { btn.textContent = t('ui.copy'); btn.classList.remove('copied'); }, 2000);
  }).catch(() => showToast('error', t('ui.err.copyFailed')));
};

/* ─────────────────────────────────────────────────────────────
   5. AppState
───────────────────────────────────────────────────────────── */
const AppState = {
  view: 'home',
  mode: 'learning',
  model: 'gemini-2.5-flash',
  lang: 'zh',
  projectId: 'default',
  projectName: '',
  userId: (() => {
    let uid = localStorage.getItem('vp_uid');
    if (!uid) { uid = 'user-' + Math.random().toString(36).slice(2, 10); localStorage.setItem('vp_uid', uid); }
    return uid;
  })(),
  settings: {
    stream: true,
    level: 'undergraduate',
    maxTheorems: 5,
    attachments: [],   // [{name, size, content}]
    memoryEnabled: true,
    citationCheck: true,
    kbConstrained: false,  // 仅在知识库范围内回答
    // 审查选项
    checkLogic: true,      // 审查逻辑漏洞
    checkCitations: true,  // 核查定理引用
    checkSymbols: true,    // 检查符号一致性
    // 深度思考
    extendedThinking: false,  // Extended Thinking（仅支持 Claude 模型）
  },
  history: [],
  isStreaming: false,
  _abortController: null,

  set(key, value) {
    if (key in this.settings) { this.settings[key] = value; }
    else { this[key] = value; }
    UI.sync(key, value);
  }
};

/* ─────────────────────────────────────────────────────────────
   5.1 附件管理（DeepSeek 风格 chip）
───────────────────────────────────────────────────────────── */
const Attachments = {
  add(file, content, rawFile) {
    AppState.settings.attachments.push({
      name: file.name,
      size: file.size,
      content,      // text content (null for PDFs)
      rawFile: rawFile || null,  // raw File object for PDFs
    });
    this.render();
    updateInputPlaceholder();
  },
  remove(idx) {
    AppState.settings.attachments.splice(idx, 1);
    this.render();
    updateInputPlaceholder();
  },
  clear() {
    AppState.settings.attachments = [];
    this.render();
    updateInputPlaceholder();
  },
  render() {
    const el = document.getElementById('attachment-chips');
    if (!el) return;
    const list = AppState.settings.attachments || [];
    const visible = list.length > 0;
    el.style.display = visible ? '' : 'none';
    if (!visible) { el.innerHTML = ''; return; }
    const removeLabel = AppState.lang === 'zh' ? '移除' : 'Remove';
    el.innerHTML = list.map((a, i) => {
      const icon = /\.pdf$/i.test(a.name) ? '📕' : '📎';
      const meta = a.rawFile ? `${(a.size / 1024 / 1024).toFixed(1)}MB` : `${(a.size / 1024).toFixed(1)}KB`;
      return `
      <div class="attachment-chip" data-idx="${i}">
        <span class="attachment-chip-icon">${icon}</span>
        <span class="attachment-chip-name" title="${escapeHtml(a.name)}">${escapeHtml(a.name)}</span>
        <span class="attachment-chip-meta">${meta}</span>
        <button class="attachment-chip-close" data-rm="${i}"
                aria-label="${removeLabel}" title="${removeLabel}">✕</button>
      </div>`;
    }).join('');
    el.querySelectorAll('[data-rm]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const idx = parseInt(btn.dataset.rm, 10);
        if (Number.isFinite(idx)) Attachments.remove(idx);
      });
    });
  },
  /** 拼接附件 + 用户附加输入文字 → 后端用的 proof_text。 */
  buildPayload(userMsgOverride) {
    let userMsg;
    if (typeof userMsgOverride === 'string') {
      userMsg = userMsgOverride.trim();
    } else {
      const ta = document.getElementById('input-textarea');
      userMsg = (ta?.value || '').trim();
    }
    const list = AppState.settings.attachments || [];
    const filesText = list
      .map(a => `--- 文件: ${a.name} ---\n${a.content}`)
      .join('\n\n');
    const focus = userMsg ? `\n\n【审查重点】\n${userMsg}` : '';
    if (!filesText && !userMsg) return '';
    if (!filesText) return userMsg;
    return (filesText + focus).trim();
  },
};

/* ─────────────────────────────────────────────────────────────
   6. 会话历史
───────────────────────────────────────────────────────────── */
const SessionHistory = {
  _key: 'vp_sessions',
  load() {
    try { const raw = localStorage.getItem(this._key); return raw ? JSON.parse(raw) : []; }
    catch { return []; }
  },
  save(sessions) { try { localStorage.setItem(this._key, JSON.stringify(sessions.slice(0, 50))); } catch {} },
  add(title, mode, messages) {
    const sessions = this.load();
    sessions.unshift({ id: Date.now(), title, mode, ts: Date.now(), messages });
    this.save(sessions);
    refreshHistorySidebar();
  },
  // plan E：删除单条历史
  remove(id) {
    const sessions = this.load().filter(s => s.id !== id);
    this.save(sessions);
    refreshHistorySidebar();
  },
  clear() { localStorage.removeItem(this._key); refreshHistorySidebar(); }
};

function _historyGroup(ts) {
  // 按时间分组：今天 / 7 天内 / 更早
  const now = Date.now();
  const oneDay = 24 * 60 * 60 * 1000;
  const dayDiff = Math.floor((now - ts) / oneDay);
  if (dayDiff < 1) return AppState.lang === 'zh' ? '今天' : 'Today';
  if (dayDiff < 7) return AppState.lang === 'zh' ? '7 天内' : 'Past 7 days';
  if (dayDiff < 30) return AppState.lang === 'zh' ? '本月' : 'This month';
  return AppState.lang === 'zh' ? '更早' : 'Older';
}

function refreshHistorySidebar() {
  const navHistory = document.getElementById('nav-history');
  if (!navHistory) return;
  const sessions = SessionHistory.load();
  if (!sessions.length) {
    navHistory.innerHTML = `<div class="nav-empty">${t('ui.noHistory')}</div>`;
    _bindHistoryToolbar();
    return;
  }

  // plan E：按"今天 / 7 天内 / 本月 / 更早"分组
  const groups = {};
  for (const s of sessions) {
    const g = _historyGroup(s.ts || s.id);
    (groups[g] = groups[g] || []).push(s);
  }
  const modeMap = { learning: 'L', solving: 'S', reviewing: 'R', searching: 'T' };
  const groupOrder = AppState.lang === 'zh'
    ? ['今天', '7 天内', '本月', '更早']
    : ['Today', 'Past 7 days', 'This month', 'Older'];

  const clearAllLabel = AppState.lang === 'zh' ? '清空全部历史' : 'Clear all';
  let html = `<div class="history-toolbar">
    <button class="history-clear-btn" id="btn-history-clear" title="${clearAllLabel}">${clearAllLabel}</button>
  </div>`;

  for (const g of groupOrder) {
    const items = groups[g];
    if (!items || !items.length) continue;
    html += `<div class="history-group-label">${g}</div>`;
    html += items.map(s => {
      const icon = modeMap[s.mode] || '?';
      const safeTitle = escapeHtml(s.title || '');
      const delLabel = AppState.lang === 'zh' ? '删除' : 'Delete';
      return `<div class="history-item" data-session-id="${s.id}" title="${safeTitle}">
        <span class="hist-mode hist-mode-${s.mode || 'learning'}">${icon}</span>
        <span class="hist-title">${safeTitle}</span>
        <button class="hist-del-btn" data-del-id="${s.id}" title="${delLabel}" aria-label="${delLabel}">×</button>
      </div>`;
    }).join('');
  }
  navHistory.innerHTML = html;

  // 绑定：点击恢复 + 点 × 删除
  navHistory.querySelectorAll('.history-item').forEach(el => {
    el.addEventListener('click', (e) => {
      if (e.target.closest('.hist-del-btn')) return;  // 点删除按钮不触发恢复
      const sid = Number(el.dataset.sessionId);
      const session = SessionHistory.load().find(s => s.id === sid);
      if (session) restoreSession(session);
    });
  });
  navHistory.querySelectorAll('.hist-del-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const sid = Number(btn.dataset.delId);
      const confirmMsg = AppState.lang === 'zh' ? '删除这条会话？' : 'Delete this session?';
      if (confirm(confirmMsg)) {
        SessionHistory.remove(sid);
        showToast('success', AppState.lang === 'zh' ? '已删除' : 'Deleted');
      }
    });
  });
  _bindHistoryToolbar();
}

function _bindHistoryToolbar() {
  const btn = document.getElementById('btn-history-clear');
  if (btn && !btn._bound) {
    btn._bound = true;
    btn.addEventListener('click', () => {
      const msg = AppState.lang === 'zh'
        ? '清空全部 ' + SessionHistory.load().length + ' 条历史？此操作不可撤销。'
        : 'Clear all ' + SessionHistory.load().length + ' sessions? This cannot be undone.';
      if (confirm(msg)) {
        SessionHistory.clear();
        showToast('success', AppState.lang === 'zh' ? '已清空' : 'Cleared');
      }
    });
  }
}

function restoreSession(session) {
  const container = document.getElementById('chat-container');
  if (!container) return;

  AppState.set('mode', session.mode);
  AppState.set('view', 'chat');
  const titleEl = document.getElementById('chat-title');
  if (titleEl) titleEl.textContent = session.title;

  container.innerHTML = '';
  (session.messages || []).forEach(msg => addMessage(msg.role, msg.content, { noSave: true }));
}

/* plan F.3 (T50)：刚切换到 chat 但还没消息时，给一个友好的空状态引导，
   避免裁判看到一个完全空白的内容区。 */
function _ensureChatEmptyState() {
  const c = document.getElementById('chat-container');
  if (!c) return;
  const hasMsg = c.querySelector('.msg-bubble, .chat-empty');
  if (hasMsg) return;
  const mode = AppState.mode || 'learning';
  const lang = AppState.lang || 'zh';
  const titles = {
    zh: { learning: '学习模式', solving: '问题求解', reviewing: '证明审查', searching: '定理检索', formalization: '形式化证明' },
    en: { learning: 'Learning', solving: 'Solving', reviewing: 'Reviewing', searching: 'Theorem Search', formalization: 'Formalization' },
  }[lang];
  const hints = {
    zh: {
      learning:      '在下方输入数学命题，AI 将分四节展开：数学背景 / 前置知识 / 完整证明 / 具体例子。',
      solving:       '输入待证命题，AI 将生成完整的分步证明，自动核查引用，置信度不足时主动拒绝。',
      reviewing:     '上传数学论文 PDF（或粘贴证明文本），AI 将逐步审查逻辑漏洞、引用的定理与符号一致性。',
      searching:     '输入关键词或公式描述，从 1kw+ 定理库中检索，获取定理的真实来源与论文出处。',
      formalization: '输入数学命题，系统将先搜索 mathlib4，若未找到则用 LLM 自动生成 Lean 4 代码，并本地编译验证。（测试版）',
    },
    en: {
      learning:      'Type a theorem below; the AI produces 4 sections: background / prerequisites / proof / examples.',
      solving:       'Enter a statement; the AI generates a complete step-by-step proof, verifies citations, and refuses if confidence is insufficient.',
      reviewing:     'Upload a math paper PDF (or paste proof text); the AI will audit logical gaps, cited theorems and notation.',
      searching:     'Search 10M+ theorems; get real sources and paper origins for any result.',
      formalization: 'Enter a math statement; the system searches mathlib4 first, then auto-generates Lean 4 code with local compilation. (Beta)',
    },
  }[lang];
  const examplesByMode = {
    learning: {
      zh: ['证明：素数有无穷多个', '解释柯西积分公式的几何意义', '证明：实数的完备性等价于有界单调收敛'],
      en: ['Prove: there are infinitely many primes', 'Explain the geometric meaning of the Cauchy integral formula', 'Prove the intermediate value theorem from first principles'],
    },
    solving: {
      zh: [
        { label: 'FP #4 · $p \\boxplus_n q$ 不等式', text: '设 $p(x)$ 和 $q(x)$ 是两个 $n$ 次首一多项式：\n$$p(x) = \\sum_{k=0}^{n} a_k x^{n-k}, \\quad q(x) = \\sum_{k=0}^{n} b_k x^{n-k},$$\n其中 $a_0 = b_0 = 1$。定义 $(p \\boxplus_n q)(x) = \\sum_{k=0}^{n} c_k x^{n-k}$，其中\n$$c_k = \\sum_{i+j=k} \\frac{(n-i)!(n-j)!}{n!(n-k)!} a_i b_j, \\quad k=0,1,\\ldots,n.$$\n对首一多项式 $p(x) = \\prod_{i \\leq n}(x - \\lambda_i)$，定义\n$$\\Phi_n(p) := \\left(\\sum_{i \\leq n} \\prod_{j \\neq i} \\frac{1}{\\lambda_i - \\lambda_j}\\right)^2,$$\n若 $p$ 有重根则 $\\Phi_n(p) := \\infty$。若 $p(x)$ 和 $q(x)$ 均为实根首一 $n$ 次多项式，是否有\n$$\\frac{1}{\\Phi_n(p \\boxplus_n q)} \\geq \\frac{1}{\\Phi_n(p)} + \\frac{1}{\\Phi_n(q)}?$$' },
        { label: 'FP #6 · $\\epsilon$-轻子集', text: '设图 $G = (V, E)$，令 $G_S = (V, E(S,S))$ 为顶点集相同但仅保留 $S$ 内部边的导出子图。设 $L$ 为 $G$ 的 Laplace 矩阵，$L_S$ 为 $G_S$ 的 Laplace 矩阵。称顶点子集 $S$ 是 $\\epsilon$-轻的，若矩阵 $\\epsilon L - L_S$ 是半正定的。是否存在常数 $c > 0$，使得对任意图 $G$ 和任意 $0 \\leq \\epsilon \\leq 1$，$V$ 中均含有大小至少为 $c\\epsilon|V|$ 的 $\\epsilon$-轻子集 $S$？' },
      ],
      en: [
        { label: 'FP #4 · $p \\boxplus_n q$ inequality', text: 'Let $p(x)$ and $q(x)$ be two monic polynomials of degree $n$:\n$$p(x) = \\sum_{k=0}^{n} a_k x^{n-k} \\quad \\text{and} \\quad q(x) = \\sum_{k=0}^{n} b_k x^{n-k},$$\nwhere $a_0 = b_0 = 1$. Define $(p \\boxplus_n q)(x) = \\sum_{k=0}^{n} c_k x^{n-k}$ where\n$$c_k = \\sum_{i+j=k} \\frac{(n-i)!(n-j)!}{n!(n-k)!} a_i b_j \\quad \\text{for } k = 0,1,\\dots,n.$$\nFor a monic polynomial $p(x) = \\prod_{i \\leq n} (x - \\lambda_i)$, define\n$$\\Phi_n(p) := \\left( \\sum_{i \\leq n} \\prod_{j \\neq i} \\frac{1}{\\lambda_i - \\lambda_j} \\right)^2$$\nand $\\Phi_n(p) := \\infty$ if $p$ has a multiple root. Is it true that if $p(x)$ and $q(x)$ are monic real-rooted polynomials of degree $n$, then\n$$\\frac{1}{\\Phi_n(p \\boxplus_n q)} \\geq \\frac{1}{\\Phi_n(p)} + \\frac{1}{\\Phi_n(q)} \\; ?$$' },
        { label: 'FP #6 · $\\epsilon$-light subsets', text: 'For a graph $G = (V, E)$, let $G_S = (V, E(S,S))$ denote the graph with the same vertex set, but only the edges between vertices in $S$. Let $L$ be the Laplacian matrix of $G$ and let $L_S$ be the Laplacian of $G_S$. A set of vertices $S$ is $\\epsilon$-light if the matrix $\\epsilon L - L_S$ is positive semidefinite. Does there exist a constant $c > 0$ so that for every graph $G$ and every $\\epsilon$ between $0$ and $1$, $V$ contains an $\\epsilon$-light subset $S$ of size at least $c\\epsilon |V|$?' },
      ],
      attribution: { zh: { text: '来自 First Proof 问题集', url: 'https://1stproof.org/first-batch.html' }, en: { text: 'From the First Proof benchmark', url: 'https://1stproof.org/first-batch.html' } },
    },
    reviewing: {
      zh: [
        { label: 'Lagrange 定理（群论）', text: '**定理**：设 $G$ 是有限群，$H$ 是 $G$ 的子群，则 $|H|$ 整除 $|G|$。\n\n**证明**：考虑 $G$ 关于 $H$ 的左陪集分解。对任意 $g \\in G$，定义左陪集 $gH = \\{gh \\mid h \\in H\\}$。\n\n首先，$gH$ 与 $H$ 等势，因为映射 $h \\mapsto gh$ 是双射。\n\n其次，两个左陪集 $g_1H$ 和 $g_2H$ 要么相等，要么不交。证明：若 $g_1H \\cap g_2H \\neq \\emptyset$，取 $x \\in g_1H \\cap g_2H$，则 $x = g_1h_1 = g_2h_2$，得 $g_1 = g_2h_2h_1^{-1} \\in g_2H$，故 $g_1H \\subseteq g_2H$。对称地 $g_2H \\subseteq g_1H$，因此 $g_1H = g_2H$。\n\n因此 $G$ 被划分为若干两两不交的左陪集，设有 $k$ 个陪集，则 $|G| = k|H|$，即 $|H|$ 整除 $|G|$。$\\square$' },
        { label: '行列式与特征值', text: '**定理**：$n$ 阶方阵的行列式等于其特征值之积。\n\n**证明**：设 $A$ 是 $n$ 阶复方阵，特征值为 $\\lambda_1, \\ldots, \\lambda_n$（重根按重数计）。\n\n在复数域上，$A$ 相似于 Jordan 标准型 $J$，即存在可逆矩阵 $P$ 使得 $A = PJP^{-1}$。\n\n由行列式的相似不变性：$\\det(A) = \\det(PJP^{-1}) = \\det(P)\\det(J)\\det(P^{-1}) = \\det(J)$。\n\nJordan 标准型 $J$ 是分块对角矩阵，每个 Jordan 块对应一个特征值。$J$ 是上三角矩阵，其行列式等于主对角线元素之积，即 $\\det(J) = \\lambda_1 \\cdots \\lambda_n$。\n\n因此 $\\det(A) = \\lambda_1 \\cdots \\lambda_n$。$\\square$' },
        { label: '素数无穷性（欧几里得）', text: '**定理**：素数有无穷多个。\n\n**证明**（欧几里得）：假设素数只有有限个，记为 $p_1, p_2, \\ldots, p_n$。\n\n考察数 $N = p_1 p_2 \\cdots p_n + 1$。\n\n由于 $N > 1$，根据算术基本定理，$N$ 可分解为素因数之积。设 $p$ 是 $N$ 的某个素因数。\n\n若 $p$ 是 $p_1, \\ldots, p_n$ 中的某个，不妨设 $p = p_i$，则 $p \\mid p_1 \\cdots p_n$ 且 $p \\mid N$，故 $p \\mid (N - p_1 \\cdots p_n) = 1$，矛盾。\n\n因此 $p$ 不在 $\\{p_1, \\ldots, p_n\\}$ 中，这与"所有素数为 $p_1, \\ldots, p_n$"矛盾。\n\n故素数有无穷多个。$\\square$' },
      ],
      en: [
        { label: "Lagrange's theorem (group theory)", text: '**Theorem**: Let $G$ be a finite group and $H$ a subgroup. Then $|H|$ divides $|G|$.\n\n**Proof**: Consider the partition of $G$ into left cosets of $H$. For any $g \\in G$, define $gH = \\{gh \\mid h \\in H\\}$.\n\nFirst, $|gH| = |H|$ since the map $h \\mapsto gh$ is a bijection.\n\nSecond, two cosets $g_1H$ and $g_2H$ are either equal or disjoint. Proof: if $g_1H \\cap g_2H \\neq \\emptyset$, take $x = g_1h_1 = g_2h_2$, then $g_1 = g_2h_2h_1^{-1} \\in g_2H$, so $g_1H \\subseteq g_2H$. By symmetry $g_2H \\subseteq g_1H$, hence $g_1H = g_2H$.\n\nThus $G$ is partitioned into $k$ disjoint cosets, so $|G| = k|H|$, i.e., $|H|$ divides $|G|$. $\\square$' },
        { label: 'Determinant equals product of eigenvalues', text: '**Theorem**: The determinant of an $n \\times n$ matrix equals the product of its eigenvalues.\n\n**Proof**: Let $A$ be an $n \\times n$ complex matrix with eigenvalues $\\lambda_1, \\ldots, \\lambda_n$ (counted with multiplicity).\n\nOver $\\mathbb{C}$, $A$ is similar to its Jordan normal form $J$: there exists invertible $P$ such that $A = PJP^{-1}$.\n\nBy similarity invariance: $\\det(A) = \\det(PJP^{-1}) = \\det(P)\\det(J)\\det(P^{-1}) = \\det(J)$.\n\nJordan form $J$ is block diagonal with each Jordan block corresponding to an eigenvalue. $J$ is upper triangular, so $\\det(J) = \\lambda_1 \\cdots \\lambda_n$.\n\nTherefore $\\det(A) = \\lambda_1 \\cdots \\lambda_n$. $\\square$' },
        { label: 'Infinitude of primes (Euclid)', text: '**Theorem**: There are infinitely many primes.\n\n**Proof** (Euclid): Suppose there are only finitely many primes $p_1, p_2, \\ldots, p_n$.\n\nConsider $N = p_1 p_2 \\cdots p_n + 1$.\n\nSince $N > 1$, by the fundamental theorem of arithmetic, $N$ has a prime divisor $p$.\n\nIf $p \\in \\{p_1, \\ldots, p_n\\}$, say $p = p_i$, then $p \\mid p_1 \\cdots p_n$ and $p \\mid N$, so $p \\mid (N - p_1 \\cdots p_n) = 1$, contradiction.\n\nThus $p \\notin \\{p_1, \\ldots, p_n\\}$, contradicting our assumption that all primes are $p_1, \\ldots, p_n$.\n\nTherefore there are infinitely many primes. $\\square$' },
      ],
    },
    searching: {
      zh: ['Cauchy 序列收敛定理', '有限群 Lagrange 定理'],
      en: ['cauchy schwarz inequality', 'fundamental theorem of algebra'],
    },
    formalization: {
      zh: [
        {
          label: '对任意整数 $a,b$，有 $a^2 + b^2 \\ge 2ab$',
          text: '对任意整数 a, b，有 a^2 + b^2 ≥ 2ab',
        },
        {
          label: '对任意实数 $a,b$，有 $(a+b)^2 = a^2 + 2ab + b^2$',
          text: '对任意实数 a, b，有 (a + b)^2 = a^2 + 2ab + b^2',
        },
        {
          label: '对任意自然数 $a,b,c$，若 $a \\mid b$ 且 $b \\mid c$，则 $a \\mid c$',
          text: '对任意自然数 a, b, c，若 a ∣ b 且 b ∣ c，则 a ∣ c',
        },
      ],
      en: [
        {
          label: 'For any integers $a,b$, $a^2 + b^2 \\ge 2ab$',
          text: 'For any integers a and b, a^2 + b^2 ≥ 2ab',
        },
        {
          label: 'For any real numbers $a,b$, $(a+b)^2 = a^2 + 2ab + b^2$',
          text: 'For any real numbers a and b, (a + b)^2 = a^2 + 2ab + b^2',
        },
        {
          label: 'For any natural numbers $a,b,c$, if $a \\mid b$ and $b \\mid c$, then $a \\mid c$',
          text: 'For any natural numbers a, b, c, if a ∣ b and b ∣ c, then a ∣ c',
        },
      ],
      attribution: {
        zh: { text: '也可以试试 Harmonic 自动形式化', url: 'https://harmonic.fun/' },
        en: { text: 'You can also try Harmonic auto-formalization', url: 'https://harmonic.fun/' },
      },
    },
  };
  const modeExData = examplesByMode[mode] || {};
  const examples = (modeExData[lang] || modeExData.zh || modeExData || []);
  const attr = modeExData.attribution ? (modeExData.attribution[lang] || modeExData.attribution.zh) : null;
  const tipsLabel = lang === 'zh' ? '试试这些例子：' : 'Try one of these:';
  c.innerHTML = `
    <div class="chat-empty" role="region">
      <div class="ce-icon">∑</div>
      <h3 class="ce-title">${titles[mode] || titles.learning}</h3>
      <p class="ce-desc">${hints[mode] || hints.learning}</p>
      ${Array.isArray(examples) && examples.length ? `
        <div class="ce-tips-label">${tipsLabel}</div>
        <ul class="ce-examples">
          ${examples.map((e, i) => {
            const isObj = e && typeof e === 'object';
            const label = isObj ? e.label : e;
            const raw   = isObj ? e.text  : e;
            return `<li class="ce-example" data-idx="${i}" data-raw="${escapeHtml(raw)}"><span class="ce-example-main">${_renderMathText(label)}</span></li>`;
          }).join('')}
        </ul>
        ${attr ? `<div class="example-attribution"><a href="${escapeHtml(attr.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(attr.text)}</a></div>` : ''}
      ` : ''}
    </div>`;
  c.querySelectorAll('.ce-example').forEach(el => {
    renderKatexFallback(el);
    el.addEventListener('click', () => {
      const ta = document.getElementById('input-textarea');
      if (ta) {
        ta.value = el.dataset.raw || el.textContent || '';
        ta.dispatchEvent(new Event('input', { bubbles: true }));
        ta.focus();
      }
    });
  });
}

/* ─────────────────────────────────────────────────────────────
   7. UI 同步层
───────────────────────────────────────────────────────────── */
const UI = {
  sync(key, value) {
    switch (key) {
      case 'view':        this.switchView(value); break;
      case 'mode':        this.updateMode(value); break;
      case 'isStreaming': this.updateStreaming(value); break;
      case 'projectId':   this.updateProjectBadge(); break;
    }
  },

  switchView(view) {
    const homeEl  = document.getElementById('home-view');
    const chatEl  = document.getElementById('chat-view');
    const navHome = document.getElementById('nav-playground');
    const btnHome = document.getElementById('btn-home');
    const btnPin  = document.getElementById('btn-pin');
    if (!homeEl || !chatEl) return;
    if (view === 'home') {
      homeEl.style.display = '';
      chatEl.style.display = 'none';
      navHome && navHome.classList.add('active');
      // plan E：home view 时隐藏返回按钮
      if (btnHome) btnHome.style.display = 'none';
      if (btnPin)  btnPin.style.display  = 'none';
    } else {
      homeEl.style.display = 'none';
      chatEl.style.display = '';
      navHome && navHome.classList.remove('active');
      if (btnHome) btnHome.style.display = '';
      if (btnPin)  btnPin.style.display  = '';
      // plan F.3 (T50)：进入 chat 时若 container 为空，渲染一个引导占位
      _ensureChatEmptyState();
    }
  },

  updateMode(mode) {
    const isReview = mode === 'reviewing';
    const isSolving = mode === 'solving';
    const attachBtn = document.getElementById('attach-btn');
    if (attachBtn) attachBtn.style.display = isReview ? '' : 'none';
    // LaTeX 工具栏按钮：仅求解模式可见
    const latexToolbarBtn = document.getElementById('toolbar-latex-btn');
    if (latexToolbarBtn) latexToolbarBtn.style.display = isSolving ? '' : 'none';
    const chipsEl = document.getElementById('attachment-chips');
    if (chipsEl) {
      const has = (AppState.settings.attachments || []).length > 0;
      chipsEl.style.display = (isReview && has) ? '' : 'none';
    }
    if (!isReview && (AppState.settings.attachments || []).length) {
      Attachments.clear();
    }
    const maxRow = document.getElementById('param-max-theorems');
    if (maxRow) maxRow.style.display = isReview ? '' : 'none';
    // 审查选项（仅 reviewing 模式显示）
    ['param-check-logic', 'param-check-citations', 'param-check-symbols'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.style.display = isReview ? '' : 'none';
    });
    const lvlSection = document.getElementById('section-level');
    if (lvlSection) lvlSection.style.display = mode === 'learning' ? '' : 'none';
    const titleEl = document.getElementById('chat-title');
    if (titleEl && AppState.view === 'chat') titleEl.textContent = t('topbar.title') || '新对话';

    // 切换模式时自动设定对应默认模型
    const _MODE_MODELS = {
      learning:      'gemini-2.5-flash',
      solving:       'gemini-2.5-pro',
      reviewing:     'gpt-5.4',
      searching:     'gemini-2.5-flash',
      formalization: 'gpt-5.3-codex',
    };
    const _MODEL_LABELS = {
      'gemini-2.5-flash':         'Gemini 2.5 Flash',
      'gemini-2.5-pro':           'Gemini 2.5 Pro',
      'gemini-3.1-pro-preview':   'Gemini 3.1 Pro',
      'gpt-5.3-codex':            'GPT 5.3 Codex',
      'gpt-5.4':                  'GPT 5.4',
      'gpt-5':                    'GPT-5',
      'gpt-4o':                   'GPT-4o',
      'claude-sonnet-4-6':        'Claude Sonnet 4.6',
      'claude-opus-4-7':          'Claude Opus 4.7',
      'o3':                       'o3',
      'o4-mini':                  'o4-mini',
      'kimi-k2.6':                'Kimi K2.6',
    };
    const defaultModel = _MODE_MODELS[mode] || 'gemini-2.5-flash';
    AppState.model = defaultModel;
    const chipLabel = document.getElementById('model-chip-label');
    if (chipLabel) chipLabel.textContent = _MODEL_LABELS[defaultModel] || defaultModel;
    document.querySelectorAll('#model-dropdown .chip-option').forEach(li => {
      li.setAttribute('aria-selected', li.dataset.value === defaultModel ? 'true' : 'false');
    });

    _syncModeChipLabel();
    _syncModeTabs();
    document.querySelectorAll('#mode-dropdown .chip-option').forEach(li => {
      li.setAttribute('aria-selected', li.dataset.value === mode ? 'true' : 'false');
    });
    renderExamplePrompts();
    updateInputPlaceholder();
  },

  updateStreaming(isStreaming) {
    const sendBtn = document.getElementById('send-btn');
    const stopBtn = document.getElementById('stop-btn');
    if (sendBtn) {
      sendBtn.disabled = isStreaming;
      // plan F.3 (T55)：流式期间替换 tooltip，移除 (↵) 快捷键提示
      if (isStreaming) {
        sendBtn.dataset.tooltipPrev = sendBtn.dataset.tooltip || '发送 (↵)';
        sendBtn.dataset.tooltip = AppState.lang === 'zh' ? '生成中…' : 'Generating…';
        sendBtn.setAttribute('aria-label', sendBtn.dataset.tooltip);
      } else if (sendBtn.dataset.tooltipPrev) {
        sendBtn.dataset.tooltip = sendBtn.dataset.tooltipPrev;
        sendBtn.setAttribute('aria-label', AppState.lang === 'zh' ? '发送' : 'Send');
        delete sendBtn.dataset.tooltipPrev;
      }
    }
    if (stopBtn) stopBtn.style.display = isStreaming ? '' : 'none';
    document.body.classList.toggle('is-streaming', !!isStreaming);
  },

  updateProjectBadge() {
    const badge = document.getElementById('project-badge');
    const badgeName = document.getElementById('project-badge-name');
    if (!badge) return;
    if (AppState.projectId && AppState.projectId !== 'default') {
      badge.style.display = '';
      if (badgeName) badgeName.textContent = AppState.projectName || AppState.projectId;
    } else {
      badge.style.display = 'none';
    }
  }
};

function _syncModeChipLabel() {
  const label = document.getElementById('mode-chip-label');
  if (label) label.textContent = t(`modes.${AppState.mode}`);
  const iconMap = { learning: '📚', solving: '🔬', reviewing: '📄', searching: '🔍' };
  const iconEl = document.querySelector('#mode-chip .chip-icon');
  if (iconEl) iconEl.textContent = iconMap[AppState.mode] || '◆';
}

function _syncLangTopbar() {
  const btn = document.getElementById('btn-lang-topbar');
  if (!btn) return;
  btn.textContent = AppState.lang === 'zh' ? 'EN' : '中';
  btn.title = AppState.lang === 'zh' ? 'Switch to English' : '切换为中文';
}

function _syncModeTabs() {
  document.querySelectorAll('.mode-tab').forEach(tab => {
    const isActive = tab.dataset.mode === AppState.mode;
    tab.classList.toggle('active', isActive);
    tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
  });
  // 移动指示器
  const indicator = document.getElementById('mode-tab-indicator');
  const active = document.querySelector('.mode-tab.active');
  if (indicator && active) {
    const parent = active.parentElement;
    const rect = active.getBoundingClientRect();
    const parentRect = parent.getBoundingClientRect();
    indicator.style.width = rect.width + 'px';
    indicator.style.transform = `translateX(${rect.left - parentRect.left}px)`;
  }
}

function updateInputPlaceholder() {
  const ta = document.getElementById('input-textarea');
  if (!ta) return;
  if (AppState.mode === 'reviewing') {
    // 已经有附件 → 输入框只用于"审查重点"
    const hasAttach = (AppState.settings.attachments || []).length > 0;
    const key = hasAttach ? 'input.proofFocusPlaceholder' : 'input.proofPlaceholder';
    ta.placeholder = t(key);
    return;
  }
  const map = {
    learning:  { zh: '输入数学命题，AI 将分步讲解…', en: 'Enter a statement and AI will explain step-by-step…' },
    solving:   { zh: '输入待证命题，AI 自动生成完整分步证明…', en: 'Enter a statement and AI will generate a complete proof…' },
    searching: { zh: '输入定理关键词或自然语言查询…', en: 'Enter a theorem name or natural-language query…' },
  };
  ta.placeholder = map[AppState.mode]?.[AppState.lang] || t('input.placeholder');
}

/* ─────────────────────────────────────────────────────────────
   8. 示例提示词
───────────────────────────────────────────────────────────── */
function renderExamplePrompts() {
  const container = document.getElementById('prompt-chips');
  if (!container) return;

  const mode = AppState.mode;
  const lang = AppState.lang;
  const modeData = EXAMPLE_PROMPTS[mode] || {};
  const prompts  = modeData[lang] || modeData.zh || [];
  const attr     = (modeData.attribution || {})[lang] || (modeData.attribution || {}).zh;

  container.innerHTML = prompts.map((p, i) => {
    const isObj = p && typeof p === 'object';
    const label = isObj ? p.label : p;
    const rendered = _renderMathText(label);
    return `<button class="prompt-chip" data-idx="${i}" title="${escapeHtml(String(label))}">${rendered}</button>`;
  }).join('');

  // 对每个 chip 触发 KaTeX 渲染
  container.querySelectorAll('.prompt-chip').forEach(btn => renderKatexFallback(btn));

  // 去除旧的来源注记
  container.parentElement?.querySelectorAll('.example-attribution').forEach(el => el.remove());
  // 添加来源注记（如有）
  if (attr) {
    const note = document.createElement('div');
    note.className = 'example-attribution';
    note.innerHTML = `<a href="${escapeHtml(attr.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(attr.text)}</a>`;
    container.after(note);
  }

  container.querySelectorAll('.prompt-chip').forEach((btn, i) => {
    btn.addEventListener('click', () => {
      const p    = prompts[i];
      const full = (p && typeof p === 'object') ? p.text : p;
      const textarea = document.getElementById('input-textarea');
      if (textarea) { textarea.value = full; autoResize(textarea); }
      AppState.set('mode', mode);
      AppState.set('view', 'chat');
      const titleEl = document.getElementById('chat-title');
      if (titleEl) titleEl.textContent = t(`modes.${mode}`);
      document.getElementById('input-textarea')?.focus();
    });
  });
}

/* ─────────────────────────────────────────────────────────────
   9. Chip 下拉
───────────────────────────────────────────────────────────── */
let _activeDropdown = null;

function openChipDropdown(chipEl, dropdownEl) {
  closeAllDropdowns();
  const rect = chipEl.getBoundingClientRect();
  dropdownEl.style.left = rect.left + 'px';
  dropdownEl.style.bottom = (window.innerHeight - rect.top + 4) + 'px';
  dropdownEl.style.top = 'auto';
  dropdownEl.classList.add('open');
  chipEl.setAttribute('aria-expanded', 'true');
  _activeDropdown = { chipEl, dropdownEl };
}

function closeAllDropdowns() {
  if (_activeDropdown) {
    _activeDropdown.dropdownEl.classList.remove('open');
    _activeDropdown.chipEl.setAttribute('aria-expanded', 'false');
    _activeDropdown = null;
  }
}

function initChip(chipId, dropdownId, onSelect) {
  const chipEl = document.getElementById(chipId);
  const dropdownEl = document.getElementById(dropdownId);
  if (!chipEl || !dropdownEl) return;

  chipEl.addEventListener('click', (e) => {
    e.stopPropagation();
    if (_activeDropdown && _activeDropdown.chipEl === chipEl) closeAllDropdowns();
    else openChipDropdown(chipEl, dropdownEl);
  });

  chipEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      openChipDropdown(chipEl, dropdownEl);
      dropdownEl.querySelector('[role=option]')?.focus();
    }
    if (e.key === 'Escape') closeAllDropdowns();
  });

  dropdownEl.addEventListener('keydown', (e) => {
    const options = [...dropdownEl.querySelectorAll('.chip-option')];
    const idx = options.indexOf(document.activeElement);
    if (e.key === 'ArrowDown') { e.preventDefault(); options[Math.min(idx+1, options.length-1)]?.focus(); }
    if (e.key === 'ArrowUp')   { e.preventDefault(); options[Math.max(idx-1, 0)]?.focus(); }
    if (e.key === 'Escape')    { closeAllDropdowns(); chipEl.focus(); }
    if (e.key === 'Tab')       { closeAllDropdowns(); }
  });

  dropdownEl.querySelectorAll('.chip-option').forEach(li => {
    li.setAttribute('tabindex', '0');
    li.addEventListener('click', () => { onSelect(li.dataset.value, li.textContent.trim()); closeAllDropdowns(); });
    li.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onSelect(li.dataset.value, li.textContent.trim());
        closeAllDropdowns();
      }
    });
  });
}

/* ─────────────────────────────────────────────────────────────
   10. 流式渲染引擎
───────────────────────────────────────────────────────────── */
const morphdomOpts = {
  onBeforeElUpdated(fromEl, toEl) {
    if (fromEl.tagName === 'DETAILS' && fromEl.open) toEl.setAttribute('open', '');
    if (fromEl.tagName === 'INPUT' || fromEl.tagName === 'TEXTAREA') return false;
    return true;
  }
};

function smartScroll(targetEl) {
  const container = document.getElementById('chat-container');
  if (!container) return;
  const nearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 140;
  if (nearBottom) targetEl.scrollIntoView({ block: 'end', behavior: 'smooth' });
}

/* ─────────────────────────────────────────────────────────────
   等待提示轮播（数学小知识 + 使用技巧）
───────────────────────────────────────────────────────────── */
const _WAIT_TIPS = {
  zh: [
    '"问题求解"模式，专门针对研究级别的数学问题',
    '欧拉恒等式 $e^{i\\pi}+1=0$ 将 $e$、$i$、$\\pi$、$1$、$0$ 五个最重要的数字统一在一个等式里，被许多数学家票选为"最美公式"',
    '在 Project 中上传数学文献 PDF，AI 的回答将优先参考你的知识库内容',
    '素数有无穷多个——欧几里得的证明只用了五行，2300 年后没人找到更短的',
    'Ramanujan 在没有正规数学教育的情况下，靠自学发现了数千个令职业数学家震惊的公式，包括对 $1/\\pi$ 的极快收敛级数',
    '在"证明审查"模式中粘贴任意证明文本，AI 会逐步独立核验每个推理步骤的合法性',
    'Galois 在 20 岁之前就证明了五次方程没有根式解——那是 1830 年。两天后他在决斗中去世，留下一封彻夜写成的数学信',
    '定理检索可以从 1000 万+ 定理库中找到形式化声明及其论文来源和作者',
    '$\\sqrt{2}$ 是无理数的证明出自古希腊，但据说最先证明这件事的人因此被扔进了海里',
    '在 Project 里记录"开放问题"，下次打开时可以无缝接续上次的探索',
    'Fermat 在书页空白处写道"我有一个绝妙的证明，但这里地方太小写不下"——350 年后 Wiles 才给出完整证明，用了 200 页',
    '上传整本教材后，在"学习模式"提问时，AI 会优先参考你上传的书中内容来回答',
    '黎曼猜想说 $\\zeta(s)$ 的非平凡零点实部都是 $\\frac{1}{2}$。它成立了 160 年，没有人证明，也没有人找到反例',
    '柯尼斯堡七桥问题是图论的起点：欧拉 1736 年证明不存在一次走完所有桥的路径，顺便发明了图论',
    'Cantor 证明实数比自然数"更多"——无穷也有大小之分。这个结果让他的导师 Kronecker 震怒，称他为"腐蚀年轻人的败类"',
    '将一段你不确定的证明粘贴进"证明审查"，AI 会指出每个有问题的步骤并说明原因',
    '哥德尔不完备定理说：任何足够强的公理系统都存在既无法证明也无法反驳的命题——包括"本系统是无矛盾的"这个命题本身',
    '"证明审查"支持上传 .tex / .md 文件，可以直接审查你的 LaTeX 论文草稿',
    'Conway 的生命游戏只有四条规则，却能模拟自复制机器、图灵机，乃至任意计算过程',
    '数学中的"猜想"不一定是猜测——有些猜想有数百页的计算支撑，只差最后一步严格证明',
    '三体问题没有解析解，但 Poincaré 在研究它的过程中发明了拓扑学和混沌理论——两个副产品比原问题更重要',
    '切换模型下拉，可以选择不同的 AI 来处理同一个命题，比较它们证明风格的差异',
    'Hilbert 在 1900 年提出 23 个问题，其中 10 个至今悬而未决，包括黎曼猜想和 $P$ vs $NP$',
    '如果一个命题总是证明不顺，先去"定理检索"里查标准名称、经典等价形式或已知特例，通常能更快找到突破口',
    '复杂问题先拆成 2 到 3 个引理分别提问，通常比一次要求完整证明更容易得到稳定结果',
    '在"形式化证明"模式中，系统会先搜索 mathlib4 是否已有现成定理，再尝试生成 Lean 4 代码并本地编译验证',
    '很多看似正确的命题其实只差一个条件；当系统给出反例时，最值得关注的是它暴露了哪个隐藏假设',
    'Jordan 曲线定理听起来直观，但早期严格证明并不简单。数学里"显然"往往正是最需要小心的地方',
    '如果你在写论文，可以先让 AI 给出证明蓝图，再把关键步骤改写成你自己的记号和叙述风格',
  ],
  en: [
    '"Problem Solving" mode is designed for research-level mathematical questions',
    'Euler\'s identity $e^{i\\pi}+1=0$ unites the five most fundamental numbers in mathematics — voted the "most beautiful formula" by generations of mathematicians',
    'Upload math papers to your Project and the AI will prioritize your knowledge base when answering',
    'Euclid\'s proof of infinitely many primes fits in five lines and is unchanged after 2300 years',
    'Ramanujan discovered thousands of formulas — including a remarkably fast series for $1/\\pi$ — with no formal training, teaching himself from a single borrowed textbook',
    'Paste any proof into "Proof Review"; the AI verifies each logical step independently, without seeing the author\'s reasoning',
    'Galois proved the quintic has no radical solution before age 20. He spent his last night writing mathematics before dying in a duel at 21',
    'Theorem Search queries 10M+ theorems and returns real paper sources, authors, and links',
    'The irrationality of $\\sqrt{2}$ was discovered by ancient Greeks — and legend says the first person to prove it was drowned for revealing the secret',
    'Log "Open Questions" in your Project to resume complex investigations across multiple sessions',
    'Fermat wrote: "I have a truly marvelous proof, but this margin is too small to contain it." It took 350 years and 200 pages to settle',
    'After uploading a textbook, Learning Mode will prioritize your uploaded material when explaining theorems',
    'The Riemann Hypothesis says all non-trivial zeros of $\\zeta(s)$ have real part $\\frac{1}{2}$. It has stood for 160 years with no proof and no counterexample',
    'The Königsberg bridge problem launched graph theory: Euler proved in 1736 that no single path crosses each bridge exactly once — and invented a new field in the process',
    'Cantor proved that some infinities are larger than others. His mentor Kronecker called him "a corrupter of youth." History sided with Cantor',
    'Paste a proof you\'re unsure about into "Proof Review" — the AI will pinpoint exactly which steps are unjustified',
    'Gödel\'s incompleteness theorem: any sufficiently powerful system contains true statements it cannot prove — including the statement "this system is consistent"',
    '"Proof Review" supports uploading .tex / .md files, so you can review a LaTeX paper draft directly',
    'Conway\'s Game of Life has four rules and can simulate self-replicating machines, Turing machines, and arbitrary computation',
    'A "conjecture" in mathematics isn\'t just a guess — some have hundreds of pages of supporting computation, waiting only for the final rigorous proof',
    'The three-body problem has no closed-form solution, but Poincaré invented topology and chaos theory while failing to solve it — better side effects than the original goal',
    'Try different models from the dropdown on the same statement — their proof styles can vary dramatically',
    'Hilbert\'s 23 Problems from 1900: 10 remain unsolved, including the Riemann Hypothesis and $P$ vs $NP$',
    'If a statement keeps resisting proof, check "Theorem Search" for its standard name, classical equivalent forms, or known special cases — that often reveals the right entry point',
    'For difficult problems, splitting the task into 2 or 3 lemmas usually works better than asking for a complete proof in one shot',
    'In "Formalization" mode, the system first searches mathlib4 for an existing theorem, then tries to generate Lean 4 code and verify it with local compilation',
    'Many statements that look true are missing exactly one condition; when the system finds a counterexample, the real value is seeing which hidden assumption failed',
    'The Jordan curve theorem sounds intuitive, but early fully rigorous proofs were far from trivial. In mathematics, "obvious" is often where extra care is needed',
    'If you are writing a paper, you can first ask the AI for a proof blueprint, then rewrite the key steps in your own notation and expository style',
  ],
};

let _waitTipTimer = null;
let _waitTipIdx = 0;
let _waitTipInterval = 8000;   // 当前间隔（每次翻倍）
let _waitTipAppearTimer = null; // 延迟出现的计时器

function _renderMathText(text) {
  if (text === null || text === undefined) return '';
  const raw = String(text).trim();
  if (!raw) return '';
  try {
    const normalized = autoWrapMath(sanitizeLatex(raw));
    return escapeHtml(normalized).replace(/\n/g, '<br>');
  } catch {
    return escapeHtml(raw).replace(/\n/g, '<br>');
  }
}

function startWaitTips(containerEl) {
  if (_waitTipTimer || _waitTipAppearTimer) return;
  _waitTipIdx = Math.floor(Math.random() * (_WAIT_TIPS.en.length));
  _waitTipInterval = 5000;

  // 取当前语言的 tips（每次调用重新读，语言切换后自动生效）
  const getTips = () => _WAIT_TIPS[AppState.lang] || _WAIT_TIPS.en;

  // 延迟 2 秒才显示第一条
  _waitTipAppearTimer = setTimeout(() => {
    _waitTipAppearTimer = null;
    const tips = getTips();

    const bar = document.createElement('div');
    bar.className = 'wait-tip-bar';
    bar.id = 'wait-tip-bar';
    bar.innerHTML = `<span class="wait-tip-text">${_renderMathText(tips[_waitTipIdx % tips.length])}</span>`;
    containerEl.appendChild(bar);
    requestAnimationFrame(() => {
      bar.classList.add('visible');
      renderKatexFallback(bar);
    });

    // 第一条出现后，按翻倍间隔调度后续
    function scheduleNext() {
      _waitTipTimer = setTimeout(() => {
        _waitTipTimer = null;
        const curTips = getTips(); // 每次重新读，跟随当前语言
        _waitTipIdx = (_waitTipIdx + 1) % curTips.length;
        const el = document.getElementById('wait-tip-bar');
        if (!el) return;
        el.classList.remove('visible');
        setTimeout(() => {
          const el2 = document.getElementById('wait-tip-bar');
          if (!el2) return;
          el2.querySelector('.wait-tip-text').innerHTML = _renderMathText(curTips[_waitTipIdx]);
          el2.classList.add('visible');
          renderKatexFallback(el2);
        }, 400);
        _waitTipInterval = Math.min(_waitTipInterval * 2, 20000); // 5→10→20→20…
        scheduleNext();
      }, _waitTipInterval);
    }
    scheduleNext();
  }, 4000);
}

/**
 * 自动检测输入语言。
 * CJK 字符占非空格字符比例 > 10% → 'zh'，否则 'en'。
 */
function _detectLang(text) {
  if (!text) return AppState.lang || 'zh';
  const cjk = (text.match(/[一-鿿㐀-䶿＀-￯]/g) || []).length;
  const total = text.replace(/\s/g, '').length;
  return (cjk / Math.max(total, 1)) > 0.1 ? 'zh' : 'en';
}

function stopWaitTips() {
  if (_waitTipAppearTimer) { clearTimeout(_waitTipAppearTimer); _waitTipAppearTimer = null; }
  if (_waitTipTimer) { clearTimeout(_waitTipTimer); _waitTipTimer = null; }
  const el = document.getElementById('wait-tip-bar');
  if (el) {
    el.classList.remove('visible');
    setTimeout(() => el.remove(), 400);
  }
}

const AppStream = {
  msgEl: null,
  bubbleEl: null,
  rawBuffer: '',
  reasoningBuffer: '',
  renderTimer: null,
  steps: [],     // { step, message, status: 'active' | 'done' }
  thinkStartedAt: 0,
  thinkEndedAt: 0,
  thinkOpen: true,    // 思考中默认展开；正文开始后自动收起

  start(msgEl, bubbleEl) {
    this.msgEl = msgEl;
    this.bubbleEl = bubbleEl;
    this.rawBuffer = '';
    this.reasoningBuffer = '';
    this.steps = [];
    this.thinkStartedAt = 0;
    this.thinkEndedAt = 0;
    this.thinkOpen = true;
    this._firstRendered = false;
    this._rafPending = false;
    clearTimeout(this.renderTimer);
    AppState.set('isStreaming', true);
    this._render();
  },

  pushStatus(step, message) {
    if (!this.msgEl) return;
    this.steps.forEach(s => { if (s.status === 'active') s.status = 'done'; });
    if (step === 'done') {
      this._render();
      return;
    }
    const existing = this.steps.find(s => s.step === step);
    if (existing) {
      existing.status = 'active';
      existing.message = message;
    } else {
      this.steps.push({ step, message, status: 'active' });
    }
    this._render();
  },

  onReasoning(text) {
    if (!text) return;
    if (!this.thinkStartedAt) this.thinkStartedAt = Date.now();
    this.reasoningBuffer += text;
    this._scheduleRender();
  },

  onChunk(chunk) {
    if (!chunk) return;
    // 第一个正文 chunk 来到 → 思考阶段终止 + 自动收起
    if (!this.rawBuffer && this.reasoningBuffer && !this.thinkEndedAt) {
      this.thinkEndedAt = Date.now();
      this.thinkOpen = false;
    }
    this.rawBuffer += chunk;
    this._scheduleRender();
  },

  _scheduleRender() {
    // plan M.3：首帧立即 + 后续 rAF 节流，~16ms 而非 60ms
    if (!this._firstRendered) {
      this._firstRendered = true;
      this._render();
      return;
    }
    if (this._rafPending) return;
    this._rafPending = true;
    requestAnimationFrame(() => {
      this._rafPending = false;
      this._render();
    });
  },

  _buildThinkingPanel() {
    if (!this.reasoningBuffer && !this.thinkStartedAt) return '';
    const isLive = !this.thinkEndedAt;
    const elapsedMs = (this.thinkEndedAt || Date.now()) - this.thinkStartedAt;
    const elapsedSec = Math.max(1, Math.round(elapsedMs / 1000));
    const charCount = this.reasoningBuffer.length;
    const labelKey = isLive ? 'ui.think.live' : 'ui.think.finished';
    const dot = isLive ? '<span class="think-dot pulsing"></span>' : '<span class="think-dot done">∴</span>';
    const meta = `<span class="think-meta">${elapsedSec}${t('ui.think.seconds')} · ${charCount} ${t('ui.think.tokens')}</span>`;
    const open = this.thinkOpen ? 'open' : '';

    // 仅在打开时渲染流式文本，节省 DOM
    let bodyHtml = '';
    if (this.thinkOpen) {
      // plan F.3 (T55)：reasoning 体走"纯文本 + 数学保护 + KaTeX"，跳过 marked.parse —
      // 否则 marked 会把 `a_n`、`*x*` 这种数学/星号当 emphasis 解析，把 `$...$` 内的
      // 反斜杠和下划线吃掉，导致 KaTeX 失败、屏幕上出现裸 `$...$`。
      const tailCursor = isLive ? '<span class="think-cursor"></span>' : '';
      let txt = this.reasoningBuffer.replace(/\n{2,}/g, '\n');
      try {
        txt = autoWrapMath(typeof sanitizeLatex === 'function' ? sanitizeLatex(txt) : txt);
      } catch (_) {}
      const inner = escapeHtml(txt).replace(/\n/g, '<br>');
      bodyHtml = `<div class="think-body">${inner}${tailCursor}</div>`;
    }
    return `
      <details class="think-panel ${isLive ? 'live' : 'done'}" ${open}>
        <summary>
          ${dot}<span class="think-label">${t(labelKey)}</span>${meta}
        </summary>
        ${bodyHtml}
      </details>`;
  },

  _render() {
    if (!this.msgEl) return;
    const thinkHtml = this._buildThinkingPanel();
    const stepsHtml = this._buildStepsHtml();
    let bodyHtml = '';
    let isAccordion = false;
    if (this.rawBuffer) {
      const sec = (typeof parseLearningOutput === 'function') ? parseLearningOutput(this.rawBuffer, { allowEmpty: true }) : null;
      if (sec && Object.keys(sec).length > 0) {
        bodyHtml = buildAccordionHtml(sec);
        isAccordion = true;
      }
      if (!bodyHtml) bodyHtml = renderStreamingMarkdown(this.rawBuffer);
    }
    const cursor = (!isAccordion && AppState.isStreaming && this.rawBuffer) ? '<span class="stream-cursor"></span>' : '';
    const html = `<div class="msg-content">
      ${thinkHtml}
      ${stepsHtml}
      ${bodyHtml ? `<div class="msg-body">${bodyHtml}${cursor}</div>` : ''}
    </div>`;
    morphdom(this.msgEl, html, morphdomOpts);
    // plan F.3 (T55)：morphdom 会把 KaTeX 已渲染的 span 退回 `$...$` 文本，
    // 在重新调用 KaTeX 之前的浏览器画帧里就会被截图捕获到"裸露 $...$"。
    // 解决：think-body / msg-body 的内容直接用 innerHTML 重写一次（替换 morphdom 已写入的 raw 文本），
    // 然后立刻 KaTeX 渲染，避免任何中间帧暴露 raw `$...$`。
    const tb = this.msgEl.querySelector('.think-body');
    if (tb && this.thinkOpen) {
      // plan F.3 (T55)：与 _buildThinkingPanel 保持一致 —— 跳过 marked.parse，
      // 直接用 escapeHtml 防注入并保留 `$...$` 给 KaTeX 处理。
      const tailCursor = !this.thinkEndedAt ? '<span class="think-cursor"></span>' : '';
      let txt = (this.reasoningBuffer || '').replace(/\n{2,}/g, '\n');
      try { txt = autoWrapMath(typeof sanitizeLatex === 'function' ? sanitizeLatex(txt) : txt); } catch (_) {}
      const inner = escapeHtml(txt).replace(/\n/g, '<br>');
      tb.innerHTML = inner + tailCursor;
    }
    // plan D：流式过程中也渲染 KaTeX，避免完成前一直裸露 $...$
    renderKatexFallback(this.msgEl);
    smartScroll(this.msgEl);
  },

  _buildStepsHtml() {
    if (!this.steps.length) return '';
    const items = this.steps.map(s => {
      const cls = s.status === 'active' ? 'active' : 'done';
      const dot = s.status === 'active'
        ? '<span class="step-dot pulsing"></span>'
        : '<span class="step-dot done">✓</span>';
      return `<div class="thinking-step ${cls}">${dot}<span class="step-msg">${escapeHtml(s.message)}</span></div>`;
    }).join('');
    return `<div class="thinking-trace">${items}</div>`;
  },

  finish(extraHtml, replace = false) {
    clearTimeout(this.renderTimer);
    if (!this.msgEl) return;

    if (this.reasoningBuffer && !this.thinkEndedAt) this.thinkEndedAt = Date.now();
    this.thinkOpen = false;
    this.steps.forEach(s => { s.status = 'done'; });

    const thinkHtml = this._buildThinkingPanel();
    const contentHtml = replace ? '' : renderMarkdown(this.rawBuffer);
    const stepsHtml = this.steps.length
      ? `<details class="thinking-trace-collapsed"><summary>${t('ui.thinking')} · ${this.steps.length} ${AppState.lang === 'zh' ? '步' : 'steps'}</summary>${this._buildStepsHtml()}</details>`
      : '';
    const html = `<div class="msg-content">
      ${thinkHtml}
      ${stepsHtml}
      ${contentHtml ? `<div class="msg-body">${contentHtml}</div>` : ''}
      ${extraHtml || ''}
    </div>`;
    morphdom(this.msgEl, html, morphdomOpts);

    renderKatexFallback(this.msgEl);
    AppState.set('isStreaming', false);
    smartScroll(this.msgEl);

    if (this.bubbleEl) addMessageActions(this.bubbleEl, this.rawBuffer);

    this.msgEl = null;
    this.bubbleEl = null;
    this.steps = [];
    this.reasoningBuffer = '';
    this.thinkStartedAt = 0;
    this.thinkEndedAt = 0;
  }
};

/* ─────────────────────────────────────────────────────────────
   11. API 封装
───────────────────────────────────────────────────────────── */
const API_BASE = '';

async function apiSSE(endpoint, body, handlers) {
  const { onChunk, onStatus, onReasoning, onDone, onError } = handlers;
  const ctrl = new AbortController();
  AppState._abortController = ctrl;

  try {
    const resp = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: ctrl.signal,
    });

    if (!resp.ok) {
      let detail = `HTTP ${resp.status}`;
      try {
        const errData = await resp.json();
        detail = errData.detail || errData.error?.message || detail;
      } catch {}
      onError(detail);
      return;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split('\n');
      buf = lines.pop();
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const raw = line.slice(6).trim();
        if (raw === '[DONE]') { onDone(); return; }
        try {
          const obj = JSON.parse(raw);
          if (obj.chunk !== undefined) onChunk(obj.chunk);
          else if (obj.reasoning !== undefined && onReasoning) onReasoning(obj.reasoning);
          else if (obj.status !== undefined && onStatus) onStatus(obj.step, obj.status);
          else if (obj.error) onError(obj.error);
        } catch {}
      }
    }
    onDone();
  } catch (err) {
    if (err.name === 'AbortError') return;
    if (err.message && /Failed to fetch|NetworkError/i.test(err.message)) {
      onError(t('ui.err.network'));
    } else {
      onError(err.message || t('ui.err.network'));
    }
  }
}

async function apiFetch(endpoint, params, method = 'GET') {
  const url = params
    ? `${API_BASE}${endpoint}?${new URLSearchParams(params)}`
    : `${API_BASE}${endpoint}`;
  const resp = await fetch(url, { method });
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try { const e = await resp.json(); detail = e.detail || e.error?.message || detail; } catch {}
    throw new Error(detail);
  }
  return resp.json();
}

async function apiPost(endpoint, body) {
  const resp = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try { const e = await resp.json(); detail = e.detail || e.error?.message || detail; } catch {}
    throw new Error(detail);
  }
  return resp.json();
}

/* ─────────────────────────────────────────────────────────────
   12. 消息渲染
───────────────────────────────────────────────────────────── */
function addMessageActions(bubbleEl, rawText) {
  if (!bubbleEl) return;
  bubbleEl.querySelector('.msg-actions')?.remove();

  const actionsEl = document.createElement('div');
  actionsEl.className = 'msg-actions';
  actionsEl.innerHTML = `
    <button class="msg-action-btn" onclick="copyMsgText(this)">⎘ ${t('ui.copy')}</button>
    <button class="msg-action-btn thumb-btn" onclick="thumbMsg(this,'up')">↑</button>
    <button class="msg-action-btn thumb-btn" onclick="thumbMsg(this,'down')">↓</button>
  `;
  actionsEl.dataset.rawText = rawText;
  bubbleEl.appendChild(actionsEl);
}

window.copyMsgText = function(btn) {
  const raw = btn.closest('.msg-actions')?.dataset.rawText || '';
  navigator.clipboard.writeText(raw).then(() => {
    btn.textContent = `✓ ${t('ui.copied')}`;
    btn.classList.add('copied');
    setTimeout(() => { btn.innerHTML = `⎘ ${t('ui.copy')}`; btn.classList.remove('copied'); }, 2000);
  }).catch(() => showToast('error', t('ui.err.copyFailed')));
};

window.thumbMsg = function(btn, dir) {
  btn.classList.toggle('active');
  if (btn.classList.contains('active')) {
    btn.textContent = dir === 'up' ? '✓' : '✓';
    showToast('success', dir === 'up' ? '感谢反馈！' : '已记录', 1800);
  } else {
    btn.textContent = dir === 'up' ? '↑' : '↓';
  }
};

function makeThinkingHtml(message) {
  const msg = message || t('ui.thinking');
  return `<div class="msg-content">
    <div class="thinking-trace"><div class="thinking-step active">
      <span class="step-dot pulsing"></span>
      <span class="step-msg">${escapeHtml(msg)}</span>
    </div></div>
  </div>`;
}

function addMessage(role, content, opts = {}) {
  const container = document.getElementById('chat-container');
  if (!container) return null;
  // plan F.3 (T50)：第一条真实消息进入时，移除空状态引导
  container.querySelector('.chat-empty')?.remove();

  const msgEl = document.createElement('div');
  msgEl.className = `message ${role}`;

  const roleEl = document.createElement('div');
  roleEl.className = 'msg-role';
  const iconDiv = document.createElement('div');
  iconDiv.className = `msg-role-icon ${role === 'user' ? 'user-icon' : 'ai-icon'}`;
  iconDiv.textContent = role === 'user' ? 'U' : '∑';
  roleEl.appendChild(iconDiv);
  roleEl.appendChild(document.createTextNode(role === 'user' ? t('ui.role.user') : t('ui.role.ai')));

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';

  const contentEl = document.createElement('div');
  contentEl.className = 'msg-content';

  if (content) {
    contentEl.innerHTML = role === 'user'
      ? renderUserMessageHtml(content)
      : renderMarkdown(content);
    if (role === 'ai' && !opts.noSave) {
      setTimeout(() => addMessageActions(bubble, content), 50);
    }
    setTimeout(() => renderKatexFallback(contentEl), 30);
  } else if (role === 'ai') {
    bubble.innerHTML = makeThinkingHtml();
    msgEl.appendChild(roleEl);
    msgEl.appendChild(bubble);
    container.appendChild(msgEl);
    msgEl.scrollIntoView({ block: 'end', behavior: 'smooth' });

    if (!opts.noSave) AppState.history.push({ role, content: '', ts: Date.now() });
    return bubble.querySelector('.msg-content');
  }

  bubble.appendChild(contentEl);
  msgEl.appendChild(roleEl);
  msgEl.appendChild(bubble);
  container.appendChild(msgEl);
  msgEl.scrollIntoView({ block: 'end', behavior: 'smooth' });

  if (!opts.noSave) AppState.history.push({ role, content: content || '', ts: Date.now() });
  return contentEl;
}

function addErrorInline(contentEl, errText) {
  if (!contentEl) return;
  contentEl.innerHTML = `<div class="msg-error">
    <span class="msg-error-icon">!</span>
    <div class="msg-error-body">
      <div class="msg-error-title">${escapeHtml(errText)}</div>
      <button class="msg-error-retry" onclick="retryLastMessage()">${t('ui.retry')}</button>
    </div>
  </div>`;
}

let _lastAttempt = null;
window.retryLastMessage = function() {
  if (!_lastAttempt) return;
  const { mode, statement, proofText } = _lastAttempt;
  AppState.set('mode', mode);
  if (mode === 'reviewing' && proofText) {
    // 把上次内容回填到主输入框；附件已经在 chips 里
    const ta = document.getElementById('input-textarea');
    if (ta) { ta.value = proofText; autoResize(ta); }
  }
  if (statement) {
    const ta = document.getElementById('input-textarea');
    if (ta) { ta.value = statement; autoResize(ta); }
  }
  sendMessage();
};

/* ─────────────────────────────────────────────────────────────
   13. 模式处理器
───────────────────────────────────────────────────────────── */
async function handleLearning(statement) {
  _lastAttempt = { mode: 'learning', statement };
  addMessage('user', statement);
  const contentEl = addMessage('ai', null);
  if (!contentEl) return;

  // 学习模式：直接展示内容，无状态条
  contentEl.innerHTML = `<div class="learn-body" id="learn-body"></div>`;
  AppState.set('isStreaming', true);

  // 启动等待提示轮播
  startWaitTips(contentEl);

  const ctrl = new AbortController();
  AppState._abortController = ctrl;

  const bodyEl   = () => document.getElementById('learn-body');

  let rawBuffer = '';
  let stopped = false;

  try {
    const resp = await fetch('/learn', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        statement,
        level: AppState.settings.level,
        model: AppState.model,
        stream: true,
        project_id: AppState.projectId,
        user_id: AppState.userId,
        kb_constrained: AppState.settings.kbConstrained,
        lang: _detectLang(statement),
        text_attachments: (AppState.settings.attachments || [])
          .filter(a => a.content && typeof a.content === 'string')
          .map(a => a.content)
          .filter(Boolean) || undefined,
      }),
      signal: ctrl.signal,
    });

    if (!resp.ok) {
      let detail = `HTTP ${resp.status}`;
      try { const e = await resp.json(); detail = e.detail || detail; } catch {}
      throw new Error(detail);
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split('\n');
      buf = lines.pop();
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const raw = line.slice(6).trim();
        if (raw === '[DONE]') break;
        try {
          const obj = JSON.parse(raw);
          if (obj.chunk !== undefined) {
            // 过滤调试注释；将 \[...\] 规范化为 $$...$$ 避免 marked 吃掉反斜杠
            const cleanChunk = obj.chunk
              .replace(/<!--(?!vp-)[^>]*-->/g, '')
              .replace(/\\\[/g, '$$')
              .replace(/\\\]/g, '$$');
            rawBuffer += cleanChunk;
            // 流式增量：解析并渲染已有内容（不做 KaTeX，避免每帧重绘闪烁）
            const sections = parseLearningOutput(rawBuffer, { allowEmpty: true });
            const b = bodyEl();
            if (b) {
              let _html = sections ? buildAccordionHtml(sections) : '';
              if (!_html) _html = renderStreamingMarkdown(rawBuffer);
              if (_html) { b.innerHTML = _html; renderKatexFallback(b); }
            }
          } else if (obj.status !== undefined) {
            // 状态帧已移除，忽略
          } else if (obj.error) {
            throw new Error(obj.error);
          }
        } catch (parseErr) {
          if (parseErr.message && parseErr.message !== raw) throw parseErr;
        }
      }
    }
  } catch (err) {
    if (err && err.name === 'AbortError') {
      stopped = true;
    } else {
      AppState.set('isStreaming', false);
      addErrorInline(contentEl, t('ui.err.learning', { e: err.message || err }));
      showToast('error', err.message || String(err));
      return;
    }
  }

  AppState.set('isStreaming', false);

  // 最终渲染：完整解析 → accordion
  const sections = parseLearningOutput(rawBuffer);
  const b = bodyEl();
  if (b && sections) {
    const html = buildAccordionHtml(sections);
    if (html) {
      b.innerHTML = html;
      b.querySelectorAll('[data-needs-katex]').forEach(el => {
        renderKatexFallback(el);
        el.removeAttribute('data-needs-katex');
      });
      renderKatexFallback(b);
    }
  }

  // 停止等待提示轮播
  stopWaitTips();

  const bubbleEl = contentEl.closest('.msg-bubble');
  if (bubbleEl) addMessageActions(bubbleEl, rawBuffer);

  const lastHistory = AppState.history[AppState.history.length - 1];
  if (lastHistory && lastHistory.role === 'ai' && !lastHistory.content) {
    lastHistory.content = rawBuffer || '';
  }
  saveCurrentSession(statement);
  smartScroll(contentEl);
}

function _stripCotPreamble(text) {
  // Disabled: system prompts already prohibit meta-commentary,
  // and COT_STARTERS patterns are too broad for mathematical text.
  return text;
}

function parseLearningOutput(text, opts) {
  opts = opts || {};
  const allowEmpty = !!opts.allowEmpty;
  const PATTERNS = [
    { key: 'background', words: ['数学背景', 'background', 'history', '历史'] },
    { key: 'prereq',     words: ['前置知识', 'prerequisite'] },
    { key: 'proof',      words: ['完整阐释', '阐释', '完整证明', '证明', '核心直觉', 'proof', 'elaboration', 'exposition', 'core insight', 'intuition'] },
    { key: 'examples',   words: ['具体例子', '例子', '示例', 'example'] },
    { key: 'extensions', words: ['延伸', '练习', 'further', 'extension', 'exercise', 'reading', 'open'] },
  ];

  const headingRe = /^#{2}\s+(.+)$/gm;
  const headings = [];
  let m;
  while ((m = headingRe.exec(text)) !== null) {
    headings.push({ title: m[1].trim(), pos: m.index, end: m.index + m[0].length });
  }
  if (headings.length === 0) return null;

  const sections = {};
  headings.forEach((h, i) => {
    const bodyStart = h.end;
    const bodyEnd   = i + 1 < headings.length ? headings[i + 1].pos : text.length;
    let content    = text.slice(bodyStart, bodyEnd).trim();
    // Strip COT preamble: remove leading paragraphs that look like meta-commentary
    // (e.g. "The request is to...", "I will...", "However, this concept...")
    content = _stripCotPreamble(content);
    if (!content) {
      if (!allowEmpty) return;
      // plan F.3 (T55)：流式空段不再用单薄的 "..."，改为可读的等待提示 + 微动画占位骨架
      const hint = AppState.lang === 'zh' ? '正在生成本节，预计 5–15 秒…' : 'Generating this section, ~5–15s…';
      content = `<div class="section-skeleton" aria-live="polite"><span class="skeleton-line"></span><span class="skeleton-line short"></span><span class="skeleton-hint">${hint}</span></div>`;
    }

    const titleLower = h.title.toLowerCase();
    const def = PATTERNS.find(p => p.words.some(w => titleLower.includes(w.toLowerCase())));
    if (!def) return;

    if (sections[def.key]) {
      sections[def.key].content += '\n\n' + content;
    } else {
      sections[def.key] = { title: h.title, content };
    }
  });

  return Object.keys(sections).length > 0 ? sections : null;
}

function buildAccordionHtml(sections, opts) {
  if (!sections) return '';
  opts = opts || {};
  // 流式期间所有 section 默认展开，让用户实时看到生成；最终态保持 prereq+proof 展开，其余可折叠
  const expandAll = !!opts.expandAll || AppState.isStreaming;

  const ORDER  = ['background', 'prereq', 'proof', 'examples', 'extensions'];
  const ICONS  = { background: '◉', prereq: '◔', proof: '◧', examples: '◑', extensions: '◐' };
  const LABELS = {
    background: t('ui.accordion.background'),
    prereq:     t('ui.accordion.prereq'),
    proof:      t('ui.accordion.proof'),
    examples:   t('ui.accordion.examples'),
    extensions: t('ui.accordion.extensions'),
  };

  return ORDER
    .filter(key => sections[key] && sections[key].content.trim())
    .map(key => {
      const { content } = sections[key];
      const label   = LABELS[key];
      const icon    = ICONS[key];
      const bodyHtml = renderMarkdown(content);
      const open = expandAll || key === 'proof' || key === 'background' ? 'open' : '';
      // 每个 accordion body 在插入 DOM 后需要触发 KaTeX 渲染，用 data 属性标记
      return `
        <details class="accordion" ${open} data-needs-katex="1">
          <summary>
            <span class="accordion-section-icon">${icon}</span>${label}
          </summary>
          <div class="accordion-body">${bodyHtml}</div>
        </details>`;
    }).join('');
}

async function handleSolving(statement) {
  _lastAttempt = { mode: 'solving', statement };
  addMessage('user', statement);

  // solving 模式：不用 AppStream（不展示 CoT），改用专属的步骤进度 UI
  const contentEl = addMessage('ai', null);
  if (!contentEl) return;

  // 初始化求解 UI
  contentEl.innerHTML = _buildSolveShell();
  AppState.set('isStreaming', true);

  // 启动等待提示轮播
  startWaitTips(contentEl);

  let rawBuffer = '';
  let metadata = { confidence: 0, verdict: 'unproven', references: [] };

  const updateStatus = (msg) => {
    const pill = contentEl.querySelector('.solve-status-pill .solve-status-text');
    if (pill) pill.textContent = msg;
  };

  const pushStep = (step, msg) => {
    // 把上一个 active step 标为 done
    contentEl.querySelectorAll('.solve-step.active').forEach(el => {
      el.classList.remove('active');
      el.classList.add('done');
      const dot = el.querySelector('.solve-step-dot');
      if (dot) dot.textContent = '✓';
    });
    // 添加新步骤
    const list = contentEl.querySelector('.solve-steps');
    if (!list) return;
    const item = document.createElement('div');
    item.className = 'solve-step active';
    item.innerHTML = `<span class="solve-step-dot pulsing"></span><span class="solve-step-msg">${escapeHtml(msg)}</span>`;
    list.appendChild(item);
    item.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  };

  const ctrl = new AbortController();
  AppState._abortController = ctrl;

  try {
    const resp = await fetch('/solve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        statement,
        model: AppState.model,
        stream: true,
        project_id: AppState.projectId,
        user_id: AppState.userId,
        lang: _detectLang(statement),
        text_attachments: (AppState.settings.attachments || [])
          .filter(a => a.content && typeof a.content === 'string')
          .map(a => a.content)
          .filter(Boolean) || undefined,
      }),
      signal: ctrl.signal,
    });

    if (!resp.ok) {
      let detail = `HTTP ${resp.status}`;
      try { const e = await resp.json(); detail = e.detail || detail; } catch {}
      throw new Error(detail);
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split('\n');
      buf = lines.pop();
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const raw = line.slice(6).trim();
        if (raw === '[DONE]') {
          break;
        }
        try {
          const obj = JSON.parse(raw);
          if (obj.chunk !== undefined) {
            rawBuffer += obj.chunk;
          } else if (obj.status !== undefined) {
            const step = obj.step || '';
            if (step === 'done') {
              contentEl.querySelectorAll('.solve-step.active').forEach(el => {
                el.classList.remove('active');
                el.classList.add('done');
                const dot = el.querySelector('.solve-step-dot');
                if (dot) dot.textContent = '✓';
              });
            } else {
              pushStep(step, obj.status);
            }
          } else if (obj.error) {
            throw new Error(obj.error);
          }
        } catch (parseErr) {
          if (parseErr.message && parseErr.message !== raw) throw parseErr;
        }
      }
    }
  } catch (err) {
    if (err && err.name === 'AbortError') {
      _finalizeSolve(contentEl, rawBuffer, metadata, statement, true);
      return;
    }
    AppState.set('isStreaming', false);
    addErrorInline(contentEl, t('ui.err.solving', { e: err.message || err }));
    showToast('error', err.message || String(err));
    return;
  }

  _finalizeSolve(contentEl, rawBuffer, metadata, statement, false);
}

function _buildSolveShell() {
  const isZh = AppState.lang === 'zh';
  return `
    <div class="solve-status-pill">
      <span class="spinner" aria-hidden="true"></span>
      <span class="solve-status-text">${isZh ? '启动求解…' : 'Starting…'}</span>
    </div>
    <div class="solve-steps"></div>
    <div class="solve-layout">
      <div class="solve-body"></div>
      <div class="solve-latex-panel" style="display:none">
        <div class="solve-latex-header">
          <span class="solve-latex-title">LaTeX</span>
          <div class="solve-latex-actions">
            <span class="solve-latex-status"></span>
            <button class="solve-latex-copy-btn" title="${isZh ? '复制 LaTeX' : 'Copy LaTeX'}">${isZh ? '复制' : 'Copy'}</button>
          </div>
        </div>
        <pre class="solve-latex-code"><code></code></pre>
      </div>
    </div>`;
}

function _finalizeSolve(contentEl, rawBuffer, metadata, statement, stopped) {
  AppState.set('isStreaming', false);
  stopWaitTips();

  // 移除进度 UI，替换为最终内容
  const stepsEl = contentEl.querySelector('.solve-steps');
  const pillEl = contentEl.querySelector('.solve-status-pill');
  if (pillEl) {
    pillEl.classList.add('done');
    const txt = pillEl.querySelector('.solve-status-text');
    if (txt) txt.textContent = stopped ? '已停止' : '求解完成';
  }
  if (stepsEl) {
    stepsEl.querySelectorAll('.solve-step.active').forEach(el => {
      el.classList.remove('active');
      el.classList.add('done');
      const dot = el.querySelector('.solve-step-dot');
      if (dot) dot.textContent = stopped ? '■' : '✓';
    });
  }

  // 渲染证明正文
  const bodyEl = contentEl.querySelector('.solve-body');
  if (bodyEl && rawBuffer) {
    bodyEl.innerHTML = renderMarkdown(rawBuffer);
    renderKatexFallback(bodyEl);
  }

  // 提取 metadata 并渲染 verdict bar
  extractSolveMetadata(rawBuffer, metadata);
  const verdictHtml = buildVerdictBar(metadata);
  if (verdictHtml) {
    const vEl = document.createElement('div');
    vEl.innerHTML = verdictHtml;
    contentEl.appendChild(vEl);
  }

  // 添加操作按钮
  const bubbleEl = contentEl.closest('.msg-bubble');
  if (bubbleEl) addMessageActions(bubbleEl, rawBuffer);

  // 存历史
  const lastHistory = AppState.history[AppState.history.length - 1];
  if (lastHistory && lastHistory.role === 'ai' && !lastHistory.content) {
    lastHistory.content = rawBuffer || '';
  }
  saveCurrentSession(statement);
  smartScroll(contentEl);

  // 自动生成 LaTeX（仅当工具栏开关打开，且有实质证明内容时）
  const latexToolbarBtn = document.getElementById('toolbar-latex-btn');
  const wantLatex = latexToolbarBtn?.dataset.active === 'true';
  if (!stopped && wantLatex && rawBuffer && rawBuffer.length > 100 &&
      !/No confident solution/i.test(rawBuffer) &&
      !/counterexample/i.test(rawBuffer.slice(0, 200))) {
    _streamLatexPanel(contentEl, rawBuffer);
  }
}

async function _streamLatexPanel(contentEl, blueprint) {
  const panel = contentEl.querySelector('.solve-latex-panel');
  if (!panel) return;
  panel.style.display = '';

  const codeEl = panel.querySelector('code');
  const statusEl = panel.querySelector('.solve-latex-status');
  const copyBtn = panel.querySelector('.solve-latex-copy-btn');
  const isZh = AppState.lang === 'zh';

  if (statusEl) statusEl.textContent = isZh ? '生成中…' : 'Generating…';

  // Strip markdown code fences so the output is directly pasteable into Overleaf
  const _stripFences = s => s
    .replace(/^```(?:latex|tex)?\s*\n?/i, '')
    .replace(/\n?```\s*$/i, '')
    .trim();

  let latex = '';

  copyBtn?.addEventListener('click', () => {
    if (!latex) return;
    const clean = _stripFences(latex);
    navigator.clipboard.writeText(clean).then(() => {
      const prev = copyBtn.textContent;
      copyBtn.textContent = isZh ? '已复制!' : 'Copied!';
      setTimeout(() => { copyBtn.textContent = prev; }, 1500);
    }).catch(() => {
      const ta = document.createElement('textarea');
      ta.value = clean;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    });
  });

  try {
    const resp = await fetch('/solve_latex', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ blueprint, model: AppState.model }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    let buf = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split('\n');
      buf = lines.pop();
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const raw = line.slice(6).trim();
        if (raw === '[DONE]') break;
        try {
          const obj = JSON.parse(raw);
          if (obj.chunk !== undefined) {
            latex += obj.chunk;
            if (codeEl) codeEl.textContent = _stripFences(latex);
          }
        } catch {}
      }
    }

    if (statusEl) statusEl.textContent = isZh ? '完成' : 'Done';
    if (copyBtn) copyBtn.disabled = false;

    // Overleaf 提示
    const noteEl = document.createElement('div');
    noteEl.className = 'solve-overleaf-note';
    noteEl.innerHTML = isZh
      ? `推荐使用 <a href="https://www.overleaf.com" target="_blank" rel="noopener noreferrer">Overleaf 在线编译器</a> 编译此 LaTeX 文件`
      : `Compile with <a href="https://www.overleaf.com" target="_blank" rel="noopener noreferrer">Overleaf online compiler</a>`;
    panel.appendChild(noteEl);
  } catch (e) {
    if (statusEl) statusEl.textContent = isZh ? `失败: ${e.message}` : `Error: ${e.message}`;
  }
}

/**
 * 鲁棒的置信度/判定提取：
 *   - 兼容 "**置信度** 87%"、"**置信度：** 87%"、"置信度: 87"、"置信度：87.0%"、"Confidence: 87%"
 *   - 全角/半角冒号、可选 markdown 加粗、可选百分号
 */
function extractSolveMetadata(text, meta) {
  const stripped = text.replace(/\*+/g, '').replace(/[：]/g, ':');

  const confM = stripped.match(/(?:置信度|confidence)\s*:?\s*([\d.]+)\s*%?/i);
  if (confM) {
    let v = parseFloat(confM[1]);
    if (!Number.isNaN(v)) {
      // 接受 0-1 (0.87) 或 0-100 (87) 两种形式
      if (v <= 1.0) v = v * 100;
      meta.confidence = Math.max(0, Math.min(100, v));
    }
  }

  const verdM = stripped.match(/(?:判定|verdict)\s*:?\s*([^\n,，。;；]+)/i);
  if (verdM) {
    const raw = verdM[1].toLowerCase().trim();
    if (/proved|direct[\s_-]?hit/.test(raw))               meta.verdict = 'proved';
    else if (/partial/.test(raw))                          meta.verdict = 'partial';
    else if (/no[\s_-]?confident/.test(raw))               meta.verdict = 'no confident solution';
    else if (/refused|unproven/.test(raw))                 meta.verdict = 'unproven';
    else if (/unverifiable/.test(raw))                     meta.verdict = 'unverifiable';
    else if (raw.length < 30)                              meta.verdict = raw.replace(/[*_]/g, '');
  }

  const refMatches = [...text.matchAll(/[-*]\s*([✓✗])\s+(.+?)\s+\((verified|not_found|error)\)/g)];
  meta.references = refMatches.map(m => ({
    ok: m[1] === '✓', name: m[2].trim(), status: m[3],
  }));
}

function buildVerdictBar(meta) {
  const pct = Math.min(Math.max(Math.round(meta.confidence), 0), 100);
  const verdictKey = meta.verdict.toLowerCase();
  const verdictMap = {
    'proved': { cls: 'proved', icon: '✓' },
    'direct_hit': { cls: 'proved', icon: '⊕' },
    'partial': { cls: 'partial', icon: '◐' },
    'unproven': { cls: 'unproven', icon: '◌' },
    'no confident solution': { cls: 'refused', icon: '⊘' },
    'unverifiable': { cls: 'refused', icon: '?' },
    'error': { cls: 'refused', icon: '⚠' },
  };
  const vd = verdictMap[verdictKey] || { cls: 'unproven', icon: '◌' };
  const labelKey = `ui.status.${verdictKey}`;
  const verdictLabel = t(labelKey) !== labelKey ? t(labelKey) : meta.verdict;
  const fillCls = pct >= 70 ? 'high' : pct >= 40 ? 'medium' : 'low';

  const refsHtml = '';

  const memHtml = (meta.memCount > 0 && AppState.settings.memoryEnabled)
    ? `<div class="memory-hint">◌ ${t('ui.status.memHint', { n: meta.memCount })}</div>`
    : '';

  return `
    <div class="verdict-bar">
      <span class="verdict-badge ${vd.cls}"><span class="verdict-icon">${vd.icon}</span>${escapeHtml(verdictLabel)}</span>
      <div class="confidence-bar">
        <span class="confidence-label">${t('ui.status.confidence')}</span>
        <div class="confidence-track"><div class="confidence-fill ${fillCls}" style="width:${pct}%"></div></div>
        <span class="confidence-num">${pct}%</span>
      </div>
      <span class="citation-count">${t('ui.status.citations')}: ${meta.references.filter(r=>r.ok).length}/${meta.references.length}</span>
    </div>
    ${refsHtml}
    ${memHtml}`;
}

/**
 * 渲染规范：禁止裸 LaTeX。所有出向用户的文本字段都走 renderMd —
 *   marked + marked-katex-extension 保证 `$...$` 由 KaTeX 转视觉数学符号；
 *   后端已 strip 掉 \label/\cite/\textbf 之类的非数学控制命令。
 */
function renderMd(text) {
  if (text === null || text === undefined) return '';
  const s = String(text).trim();
  if (!s) return '';
  try {
    return marked.parse(autoWrapMath(s));
  } catch {
    return escapeHtml(s).replace(/\n/g, '<br>');
  }
}

function renderInlineMd(text) {
  return renderMd(text).replace(/^<p>([\s\S]*)<\/p>\n?$/, '$1');
}

function autoWrapReviewMath(text) {
  if (!text) return text;
  let s = sanitizeLatex(text);
  const placeholders = [];
  const protect = (input, re) => input.replace(re, m => {
    placeholders.push(m);
    return `\u0000R${placeholders.length - 1}\u0000`;
  });

  s = protect(s, /```[\s\S]*?```/g);
  s = protect(s, /`[^`\n]+`/g);
  s = protect(s, /\$\$[\s\S]*?\$\$/g);
  s = protect(s, /\$[^$\n]+\$/g);
  s = protect(s, /\\\([\s\S]*?\\\)/g);
  s = protect(s, /\\\[[\s\S]*?\\\]/g);
  s = protect(s, /https?:\/\/\S+/g);

  s = _wrapLatexCommandsWithNestedBraces(s);
  s = s.replace(/(?<![\\$\w])(\\(?:frac|sqrt|sum|prod|int|lim|sup|inf|mathbb|mathcal|mathfrak|mathrm|mathbf|mathit|operatorname|forall|exists|in|notin|subset|subseteq|cup|cap|leq|geq|neq|to|mapsto|mid|alpha|beta|gamma|delta|epsilon|varepsilon|zeta|eta|theta|vartheta|iota|kappa|lambda|mu|nu|xi|pi|rho|sigma|tau|upsilon|phi|varphi|chi|psi|omega|Gamma|Delta|Theta|Lambda|Xi|Pi|Sigma|Phi|Psi|Omega|infty|partial|nabla|cdot|cdots|ldots|times|div|pm|mp|approx|equiv|sim|propto|circ|prime)(?:\{[^{}]*\}|\b))/g,
    '$$$1$$');

  const wrap = (re) => {
    s = s.replace(re, (m) => (m.includes('$') ? m : `$${m.trim()}$`));
  };

  // Relation/congruence fragments like `p ≡ 1 (mod 4)` or `x^2 + y^2 = z^2`.
  wrap(/(?<![$\\\w])(?:\|?[A-Za-z][A-Za-z0-9_]*\|?|\([^)]+\)|\{[^{}\n]{1,40}\})(?:\s*(?:\^|\_)\s*(?:\{[^{}]+\}|[A-Za-z0-9]+))?(?:\s*[+\-*/]\s*(?:\|?[A-Za-z0-9]+\|?|\([^)]+\)|\{[^{}\n]{1,30}\})){0,4}\s*(?:=|≡|≤|≥|<|>|∈|∉|⊂|⊆|∣|→|↦)\s*(?:[A-Za-z0-9\\][^,\n。；;:]*)/g);
  // Short set-builder or ambient set expressions like `S = {(x, y, z) ∈ N^3 : ...}`.
  wrap(/(?<![$\\\w])(?:[A-Za-z][A-Za-z0-9_]*\s*=\s*\{[^{}\n]{1,120}\}|[A-Za-z][A-Za-z0-9_]*\s*:\s*[^,\n。；;:]{1,80}(?:→|↦)[^,\n。；;:]{1,40})/g);
  // Standalone cardinality / subgroup snippets.
  wrap(/(?<![$\\\w])(?:\|[A-Za-z][A-Za-z0-9_]*\|\s*(?:\mid|∣)\s*\|[A-Za-z][A-Za-z0-9_]*\||[A-Za-z][A-Za-z0-9_]*\s*\\le\s*[A-Za-z][A-Za-z0-9_]*)/g);

  s = s.replace(/\u0000R(\d+)\u0000/g, (_, i) => placeholders[+i] || '');
  return s;
}

function renderMathText(text, { inline = false } = {}) {
  if (text === null || text === undefined) return '';
  const raw = String(text).trim();
  if (!raw) return '';
  let normalized = raw;
  try {
    normalized = autoWrapReviewMath(raw);
  } catch {}
  const safe = escapeHtml(normalized);
  if (inline) return safe.replace(/\s*\n+\s*/g, ' ');
  const blocks = safe
    .split(/\n{2,}/)
    .map(part => part.trim())
    .filter(Boolean)
    .map(part => `<p class="review-math-paragraph">${part.replace(/\n/g, '<br>')}</p>`);
  return blocks.join('') || `<p class="review-math-paragraph">${safe.replace(/\n/g, '<br>')}</p>`;
}

function stripPresentationMarkdown(text) {
  if (text === null || text === undefined) return '';
  return String(text)
    .replace(/^\s{0,3}#{1,6}\s+/gm, '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/__([^_]+)__/g, '$1')
    .replace(/`([^`]+)`/g, '$1');
}

function renderUserMessageHtml(text) {
  if (text === null || text === undefined) return '';
  const raw = stripPresentationMarkdown(String(text).trim());
  if (!raw) return '';
  let normalized = raw;
  try {
    normalized = autoWrapMath(sanitizeLatex(raw));
  } catch {}
  const safe = escapeHtml(normalized);
  const blocks = safe
    .split(/\n{2,}/)
    .map(part => part.trim())
    .filter(Boolean)
    .map(part => `<p class="user-msg-paragraph">${part.replace(/\n/g, '<br>')}</p>`);
  return `<div class="user-msg-body">${blocks.join('') || `<p class="user-msg-paragraph">${safe.replace(/\n/g, '<br>')}</p>`}</div>`;
}

function renderReviewField(label, value, { inline = false, className = '' } = {}) {
  if (value === null || value === undefined) return '';
  const raw = String(value).trim();
  if (!raw) return '';
  const content = renderMathText(raw, { inline });
  const fieldCls = `review-field ${className}`.trim();
  const valueCls = inline ? 'review-field-value inline' : 'review-field-value';
  return `
    <div class="${fieldCls}">
      <div class="review-field-label">${escapeHtml(label)}</div>
      <div class="${valueCls}">${content}</div>
    </div>`;
}

const _VERDICT_CSS_MAP = {
  'Correct': 'proved',
  'Minor Issues': 'partial',
  'Major Issues': 'partial',
  'Partial': 'partial',
  'Incorrect': 'unproven',
  'Unverifiable': 'refused',
  'Error': 'refused',
};

function renderTheoremCardHtml(tr, index) {
  const tCls = _VERDICT_CSS_MAP[tr.verdict] || 'unproven';
  const title = tr.theorem_name
    ? `${t('ui.review.theorem')} ${index}: ${renderMathText(tr.theorem_name, { inline: true })}`
    : `${t('ui.review.theorem')} ${index}`;
  const statementHtml = tr.statement
    ? `<div class="theorem-card-section theorem-card-statement">${renderReviewField(
        AppState.lang === 'zh' ? '命题' : 'Statement',
        tr.statement
      )}</div>`
    : '';
  const metaHtml = [
    tr.location_hint ? renderReviewField(AppState.lang === 'zh' ? '位置' : 'Location', tr.location_hint, { inline: true }) : '',
  ].join('');
  const stepsHtml = (tr.proof_steps || []).map(s => `
    <div class="issue-item">
      <span class="issue-level ${(s.verdict || 'info').toLowerCase()}">${escapeHtml(s.verdict || '')}</span>
      <div class="issue-content">
        ${renderReviewField(AppState.lang === 'zh' ? '说明' : 'Reason', s.reason || s.text || '')}
      </div>
    </div>`).join('');
  const issHtml = (tr.issues || []).map(iss => `
    <div class="issue-item">
      <span class="issue-level ${(iss.issue_type || iss.level || 'info').toLowerCase()}">${escapeHtml(iss.issue_type || iss.level || 'INFO')}</span>
      <div class="issue-content">
        ${iss.location ? renderReviewField(AppState.lang === 'zh' ? '位置' : 'Location', iss.location, { inline: true }) : ''}
        ${renderReviewField(AppState.lang === 'zh' ? '问题描述' : 'Issue', iss.description || iss.message || '')}
        ${iss.fix_suggestion ? renderReviewField(AppState.lang === 'zh' ? '修复建议' : 'Suggestion', iss.fix_suggestion) : ''}
      </div>
    </div>`).join('');
  const citesHtml = (tr.citation_checks || []).filter(c => c && c.citation).map(c => `
    <div class="issue-item">
      <span class="issue-level ${c.status === 'verified' ? 'passed' : 'gap'}">${escapeHtml(c.status || '')}</span>
      <div class="issue-content">
        ${renderReviewField(AppState.lang === 'zh' ? '引用' : 'Citation', c.citation || '')}
        ${c.matched ? renderReviewField(AppState.lang === 'zh' ? '匹配结果' : 'Matched', c.matched, { inline: true }) : ''}
      </div>
    </div>`).join('');
  const body = stepsHtml + issHtml + citesHtml;
  return `
    <div class="theorem-card" data-idx="${index}">
      <div class="theorem-card-header">
        <span class="theorem-card-name">${title}</span>
        <span class="verdict-badge ${tCls}">${escapeHtml(tr.verdict || '?')}</span>
      </div>
      ${metaHtml ? `<div class="theorem-card-meta">${metaHtml}</div>` : ''}
      ${statementHtml}
      ${body ? `<div class="theorem-card-body">${body}</div>` : ''}
    </div>`;
}

function renderReviewSummary(el, report) {
  if (!el || !report) return;
  const verdictCls = _VERDICT_CSS_MAP[report.overall_verdict] || 'unproven';
  const stats = report.stats || {};
  const isZh = AppState.lang === 'zh';
  const issuePool = (report.issues && report.issues.length)
    ? report.issues
    : (report.theorem_reviews || []).flatMap(tr =>
        (tr.issues || []).map(iss => ({
          ...iss,
          location: iss.location || tr.location_hint || tr.theorem_name || '',
        })));
  const topIssues = issuePool.slice(0, 8);
  const summaryText = topIssues.length
    ? (isZh
        ? `审查完成，共发现 ${topIssues.length} 个需要关注的问题；下面列出具体描述。`
        : `Review complete. ${topIssues.length} issue(s) need attention; concrete descriptions are listed below.`)
    : (isZh
        ? '审查完成，当前未发现明显问题。'
        : 'Review complete. No obvious issues were found.');
  const statsHtml = `
    <div class="review-stats">
      ${isZh ? '已检验' : 'Checked'} ${stats.theorems_checked || 0}
      ${isZh ? '个定理 ·' : 'theorems ·'}
      ${isZh ? '问题' : 'issues'} ${stats.issues_found || 0} ·
      ${isZh ? '引用核查' : 'citations'} ${stats.citations_checked || 0}
      ${stats.fallback === 'single_proof'
        ? (isZh ? '· 整段证明降级' : '· single-proof fallback')
        : ''}
    </div>`;
  const globalIssuesHtml = topIssues.length
    ? `<div class="review-global-issues">${topIssues.map(iss => `
        <div class="issue-item">
          <span class="issue-level ${(iss.issue_type || 'info').toLowerCase()}">${escapeHtml(iss.issue_type || 'INFO')}</span>
          <div class="issue-content">
            ${iss.location ? renderReviewField(isZh ? '位置' : 'Location', iss.location, { inline: true }) : ''}
            ${renderReviewField(isZh ? '问题描述' : 'Issue', iss.description || iss.message || '')}
            ${iss.fix_suggestion ? renderReviewField(isZh ? '修复建议' : 'Suggestion', iss.fix_suggestion) : ''}
          </div>
        </div>`).join('')}</div>`
    : `<div class="review-global-issues">
        <div class="issue-item">
          <span class="issue-level passed">${isZh ? '结果' : 'Result'}</span>
          <div class="issue-content">${renderReviewField(isZh ? '摘要' : 'Summary', summaryText)}</div>
        </div>
      </div>`;
  el.innerHTML = `
    <div class="review-overall">
      <span class="review-overall-label">${t('ui.review.overall')}</span>
      <span class="verdict-badge ${verdictCls}">${escapeHtml(report.overall_verdict || '?')}</span>
    </div>
    <div class="review-summary-text">${renderMathText(summaryText)}</div>
    ${globalIssuesHtml}
    ${statsHtml}`;
  // 数学公式渲染兜底
  try { renderKatexFallback(el); } catch {}
}

/** SSE 流式审查：fetch + ReadableStream，解析 status / result / final / [DONE]。 */
async function streamReview(proofText, { onStatus, onResult, onFinal, onError, lang } = {}) {
  const ctrl = new AbortController();
  AppState._abortController = ctrl;
  AppState.set('isStreaming', true);
  try {
    const resp = await fetch(`${API_BASE}/review_stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        proof_text: proofText,
        max_theorems: AppState.settings.maxTheorems,
        user_id: AppState.userId,
        lang: lang || _detectLang(proofText),
        check_logic: AppState.settings.checkLogic !== false,
        check_citations: AppState.settings.checkCitations !== false,
        check_symbols: AppState.settings.checkSymbols !== false,
        extended_thinking: AppState.settings.extendedThinking === true,
      }),
      signal: ctrl.signal,
    });
    if (!resp.ok) {
      let detail = `HTTP ${resp.status}`;
      try {
        const e = await resp.json();
        detail = e.detail || e.error?.message || detail;
      } catch {}
      throw new Error(detail);
    }
    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    let buf = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split('\n');
      buf = lines.pop();
      for (const raw of lines) {
        const line = raw.trim();
        if (!line.startsWith('data:')) continue;
        const body = line.slice(5).trim();
        if (!body) continue;
        if (body === '[DONE]') return;
        try {
          const obj = JSON.parse(body);
          if (obj.status !== undefined && onStatus) onStatus(obj.step || 'info', obj.status);
          else if (obj.result !== undefined && onResult) onResult(obj.result);
          else if (obj.final !== undefined && onFinal) onFinal(obj.final);
          else if (obj.error && onError) onError(obj.error);
        } catch { /* ignore malformed line */ }
      }
    }
  } finally {
    AppState.set('isStreaming', false);
  }
}

/* ─────────────────────────────────────────────────────────────
   形式化证明模式
───────────────────────────────────────────────────────────── */
async function handleFormalization(statement) {
  _lastAttempt = { mode: 'formalization', statement };
  addMessage('user', statement);

  const contentEl = addMessage('ai', null);
  if (!contentEl) return;

  await _runFormalizationRequest(
    contentEl,
    {
      statement,
      model: AppState.model,
      lang: AppState.lang,
      max_iters: 4,
    },
    { statement }
  );
}

async function _runFormalizationRequest(contentEl, payload, ctx = {}) {
  const statement = (ctx.statement || payload.statement || '').trim();

  const isZh = AppState.lang === 'zh';
  contentEl.innerHTML = _buildFormalizeShell();
  AppState.set('isStreaming', true);
  startWaitTips(contentEl);

  const pushStep = (step, msg) => {
    contentEl.querySelectorAll('.solve-step.active').forEach(el => {
      el.classList.remove('active');
      el.classList.add('done');
      const dot = el.querySelector('.solve-step-dot');
      if (dot) dot.textContent = '✓';
    });
    const list = contentEl.querySelector('.solve-steps');
    if (!list) return;
    const item = document.createElement('div');
    item.className = 'solve-step active';
    item.innerHTML = `<span class="solve-step-dot pulsing"></span><span class="solve-step-msg">${escapeHtml(msg)}</span>`;
    list.appendChild(item);
    item.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  };

  const ctrl = new AbortController();
  AppState._abortController = ctrl;
  let finalResult = null;

  try {
    const resp = await fetch('/formalize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: ctrl.signal,
    });
    if (!resp.ok) {
      let detail = `HTTP ${resp.status}`;
      try { const e = await resp.json(); detail = e.detail || detail; } catch {}
      throw new Error(detail);
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split('\n');
      buf = lines.pop();
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const raw = line.slice(6).trim();
        if (raw === '[DONE]') break;
        try {
          const obj = JSON.parse(raw);
          if (obj.status !== undefined) {
            pushStep(obj.step || 'info', obj.status);
          } else if (obj.final) {
            finalResult = obj.final;
          } else if (obj.error) {
            throw new Error(obj.error);
          }
        } catch (parseErr) {
          if (parseErr.message && parseErr.message !== raw) throw parseErr;
        }
      }
    }
  } catch (err) {
    if (err && err.name === 'AbortError') {
      _finalizeFormalize(contentEl, finalResult, true, statement);
      return;
    }
    AppState.set('isStreaming', false);
    stopWaitTips();
    addErrorInline(contentEl, t('ui.err.formalization', { e: err.message || err }));
    showToast('error', err.message || String(err));
    return;
  }

  _finalizeFormalize(contentEl, finalResult, false, statement);
}

function _buildFormalizeShell() {
  const isZh = AppState.lang === 'zh';
  return `
    <div class="solve-status-pill">
      <span class="spinner" aria-hidden="true"></span>
      <span class="solve-status-text">${isZh ? '启动形式化…' : 'Starting formalization…'}</span>
    </div>
    <div class="solve-steps"></div>
    <div class="formalize-result" style="display:none"></div>`;
}

function _finalizeFormalize(contentEl, result, stopped, statement = '') {
  AppState.set('isStreaming', false);
  stopWaitTips();
  const isZh = AppState.lang === 'zh';
  const tAction = {
    generate: isZh ? '生成候选' : 'Generate',
    repair: isZh ? '修复候选' : 'Repair',
    replan: isZh ? '重规划' : 'Re-plan',
    seed: isZh ? '继续优化' : 'Resume',
    retrieval_match: isZh ? '命中现有定理' : 'Retrieval match',
  };
  const tFailure = {
    none: isZh ? '无' : 'None',
    syntax_error: isZh ? '语法错误' : 'Syntax error',
    missing_symbol: isZh ? '缺少符号/定理' : 'Missing symbol',
    tactic_error: isZh ? '策略/战术错误' : 'Tactic error',
    statement_mismatch: isZh ? '命题偏移' : 'Statement mismatch',
    unsolved_goals: isZh ? '仍有未解目标' : 'Unsolved goals',
    mathlib_unavailable: isZh ? '本地缺少 Mathlib' : 'Mathlib unavailable',
    compile_timeout: isZh ? '编译超时' : 'Compile timeout',
    environment_unavailable: isZh ? 'Lean 环境不可用' : 'Lean unavailable',
    compile_error: isZh ? '编译错误' : 'Compile error',
  };
  const formatFailureMode = (mode) => tFailure[mode] || mode || tFailure.none;
  const formatAction = (action) => tAction[action] || action || (isZh ? '未知阶段' : 'Unknown');
  const renderBadgeList = (items = []) => items
    .filter(Boolean)
    .map(item => `<span class="formalize-pill">${escapeHtml(String(item))}</span>`)
    .join('');

  const pillEl = contentEl.querySelector('.solve-status-pill');
  if (pillEl) {
    pillEl.classList.add('done');
    const txt = pillEl.querySelector('.solve-status-text');
    if (txt) txt.textContent = stopped
      ? (isZh ? '已停止' : 'Stopped')
      : (result?.status === 'found_mathlib'
          ? (isZh ? '在 mathlib4 中找到定理' : 'Found in mathlib4')
          : (isZh ? '形式化完成' : 'Formalization complete'));
  }
  contentEl.querySelectorAll('.solve-step.active').forEach(el => {
    el.classList.remove('active');
    el.classList.add('done');
    const dot = el.querySelector('.solve-step-dot');
    if (dot) dot.textContent = stopped ? '■' : '✓';
  });

  if (!result) {
    addErrorInline(contentEl, isZh ? '形式化失败，未返回结果' : 'Formalization failed: no result returned');
    return;
  }

  const resultEl = contentEl.querySelector('.formalize-result');
  if (!resultEl) return;

  const selectedCandidate = result.selected_candidate || {};
  const lean_code    = result.lean_code    || selectedCandidate.lean_code || '';
  const source       = result.source       || 'generated';
  const source_url   = result.source_url   || '';
  const compilation  = result.compilation  || {};
  const proof_status = result.proof_status || 'statement_only';
  const explanation  = result.explanation  || '';
  const match_score  = result.match_score  || 0;
  const uses_mathlib = result.uses_mathlib;
  const iterations   = Math.max(1, Number(result.iterations || 1));
  const autoOptimized = !!result.auto_optimized;
  const blueprint = result.blueprint || null;
  const verificationTrace = Array.isArray(result.verification_trace) ? result.verification_trace : [];
  const retrievalContext = Array.isArray(result.retrieval_context) ? result.retrieval_context : [];
  const failureMode = result.failure_mode || 'none';
  const nextActionHint = result.next_action_hint || '';
  const theoremName = result.theorem_name || selectedCandidate.theorem_statement || '';

  // Compilation status badge
  const cmpStatus = compilation.status || 'unknown';
  const cmpMap = {
    verified:         ['fbadge-ok',      isZh ? '✓ 编译通过'    : '✓ Verified'],
    mathlib_verified: ['fbadge-mathlib',  isZh ? '✓ mathlib4'  : '✓ mathlib4'],
    mathlib_skip:     ['fbadge-skip',     isZh ? '需 Mathlib'   : 'Mathlib req.'],
    error:            ['fbadge-err',      isZh ? '✗ 编译错误'   : '✗ Error'],
    timeout:          ['fbadge-warn',     isZh ? '⏱ 超时'       : '⏱ Timeout'],
    unavailable:      ['fbadge-skip',     isZh ? '本地不可用'   : 'Local N/A'],
  };
  const [cmpCls, cmpTxt] = cmpMap[cmpStatus] || ['fbadge-skip', cmpStatus];

  // Proof status badge
  const proofMap = {
    complete:       ['fbadge-ok',   isZh ? '证明完整'   : 'Complete'],
    partial:        ['fbadge-warn', isZh ? '含 sorry'   : 'Has sorry'],
    statement_only: ['fbadge-skip', isZh ? '仅命题语句' : 'Stmt. only'],
  };
  const [proofCls, proofTxt] = proofMap[proof_status] || ['fbadge-skip', proof_status];

  // Source row
  let sourceHtml = '';
  if (source === 'mathlib4' && source_url) {
    const sc = match_score ? ` · ${Math.round(match_score * 100)}% ${isZh ? '匹配' : 'match'}` : '';
    sourceHtml = `<div class="formalize-source-row">
      <span class="fbadge fbadge-mathlib">mathlib4</span>
      <a href="${escapeHtml(source_url)}" target="_blank" rel="noopener noreferrer" class="formalize-source-link">${isZh ? '查看来源 →' : 'View source →'}</a>${sc}
    </div>`;
  } else {
    sourceHtml = `<div class="formalize-source-row">
      <span class="fbadge fbadge-gen">${isZh ? 'AI 生成' : 'AI-generated'}</span>
      ${source_url ? `<a href="${escapeHtml(source_url)}" target="_blank" rel="noopener noreferrer" class="formalize-source-link">${isZh ? '在 Lean Playground 验证 →' : 'Verify in Lean Playground →'}</a>` : ''}
    </div>`;
  }

  const summaryParts = [];
  if (iterations > 1) {
    summaryParts.push(`${isZh ? '尝试' : 'Attempts'}: <strong>${iterations}</strong>`);
  }
  if (failureMode !== 'none') {
    summaryParts.push(`${isZh ? '失败类型' : 'Failure mode'}: <strong>${escapeHtml(formatFailureMode(failureMode))}</strong>`);
  }
  const metaHtml = summaryParts.length
    ? `<div class="formalize-meta-row">${summaryParts.map(part => `<span>${part}</span>`).join('')}</div>`
    : '';

  const errHtml = (cmpStatus === 'error' && compilation.error)
    ? `<pre class="formalize-compile-error">${escapeHtml(compilation.error)}</pre>` : '';

  const codeHtml = lean_code ? `
    <div class="formalize-code-header">
      <span class="formalize-code-label">Lean 4</span>
      <span class="fbadge ${proofCls}">${proofTxt}</span>
      <span class="fbadge ${cmpCls}">${cmpTxt}</span>
      <button class="formalize-copy-btn" title="${isZh ? '复制代码' : 'Copy code'}">⎘ ${isZh ? '复制' : 'Copy'}</button>
    </div>
    <pre class="formalize-code"><code>${escapeHtml(lean_code)}</code></pre>
    ${errHtml}` : '';

  const betaNote = `<div class="formalize-beta-note">
    ⚠ ${isZh
      ? '测试版功能：自动形式化结果可能存在错误，建议在 Lean 环境中二次核验。'
      : 'Beta: auto-formalization results may contain errors. Always verify in a Lean environment.'}
  </div>`;

  const canContinueOptimize = (
    !stopped &&
    source === 'generated' &&
    cmpStatus === 'error' &&
    !uses_mathlib &&
    !!lean_code &&
    !!compilation.error &&
    !!statement
  );

  const actionHtml = `
    <div class="formalize-action-row">
      ${canContinueOptimize
        ? `<button type="button" class="btn-secondary formalize-action-btn formalize-optimize-btn">${isZh ? '继续优化' : 'Continue optimizing'}</button>`
        : ''}
      <a href="https://harmonic.fun/" target="_blank" rel="noopener noreferrer" class="btn-secondary formalize-action-btn">${isZh ? '试试 Harmonic 自动形式化' : 'Try Harmonic auto-formalization'}</a>
    </div>`;

  resultEl.innerHTML = sourceHtml + metaHtml + codeHtml + actionHtml + betaNote;
  resultEl.style.display = '';

  if (window.hljs) {
    resultEl.querySelectorAll('pre code').forEach(el => hljs.highlightElement(el));
  }

  const copyBtn = resultEl.querySelector('.formalize-copy-btn');
  if (copyBtn && lean_code) {
    copyBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(lean_code).then(() => {
        const orig = copyBtn.innerHTML;
        copyBtn.textContent = isZh ? '已复制！' : 'Copied!';
        setTimeout(() => { copyBtn.innerHTML = orig; }, 1500);
      }).catch(() => showToast('warn', t('ui.err.copyFailed')));
    });
  }

  const optimizeBtn = resultEl.querySelector('.formalize-optimize-btn');
  if (optimizeBtn) {
    optimizeBtn.addEventListener('click', async () => {
      optimizeBtn.disabled = true;
      optimizeBtn.textContent = isZh ? '继续优化中…' : 'Optimizing…';
      await _runFormalizationRequest(
        contentEl,
        {
          statement,
          model: AppState.model,
          lang: AppState.lang,
          max_iters: 4,
          current_code: lean_code,
          compile_error: compilation.error || '',
          skip_search: true,
        },
        { statement }
      );
    });
  }

  renderKatexFallback(resultEl);
}

async function handleReviewing(focusText) {
  focusText = (focusText || '').trim();

  const list = AppState.settings.attachments || [];
  const pdfAttach = list.find(a => a.rawFile && /\.pdf$/i.test(a.name));

  if (pdfAttach) {
    // PDF upload path: send File directly to /review_pdf_stream
    return _handleReviewingPdf(pdfAttach, focusText);
  }

  const proofText = Attachments.buildPayload(focusText);
  if (!proofText) {
    showToast('error', t('ui.err.emptyProof'));
    const ta = document.getElementById('input-textarea');
    ta?.classList.add('shake');
    setTimeout(() => ta?.classList.remove('shake'), 500);
    return;
  }
  if (proofText.length > 50000) {
    showToast('error', t('ui.err.proofTooLong'));
    return;
  }

  _lastAttempt = { mode: 'reviewing', proofText };
  let userPreview;
  if (list.length) {
    userPreview = list.map(a => '📎 ' + a.name).join('\n')
      + (focusText ? '\n\n' + focusText : '');
  } else {
    userPreview = proofText;
  }
  addMessage('user', userPreview);

  const contentEl = addMessage('ai', null);
  if (!contentEl) return;
  const isZh = AppState.lang === 'zh';
  const initText = isZh ? '正在准备…' : 'Preparing…';
  contentEl.innerHTML = `
    <div class="review-status-pill" id="rv-status">
      <span class="spinner" aria-hidden="true"></span>
      <span class="rv-status-text">${escapeHtml(initText)}</span>
    </div>
    <div class="review-cards" id="rv-cards"></div>
    <div class="review-final" id="rv-final"></div>`;

  let finalReport = null;
  const partials = [];

  try {
    await streamReview(proofText, {
      onStatus: (step, msg) => {
        const txt = contentEl.querySelector('.rv-status-text');
        if (txt) txt.textContent = msg;
        if (step === 'done') {
          contentEl.querySelector('#rv-status')?.classList.add('done');
        }
      },
      onResult: (payload) => {
        if (!payload || payload.kind !== 'theorem' || !payload.data) return;
        partials.push(payload.data);
        const cardsEl = contentEl.querySelector('#rv-cards');
        if (cardsEl) {
          cardsEl.insertAdjacentHTML('beforeend',
            renderTheoremCardHtml(payload.data, payload.index || partials.length));
          try { renderKatexFallback(cardsEl.lastElementChild); } catch {}
          smartScroll(contentEl);
        }
      },
      onFinal: (report) => {
        finalReport = report;
      },
      onError: (e) => { throw new Error(e); },
    });

    const pill = contentEl.querySelector('#rv-status');
    if (pill) pill.classList.add('done');
    const txt = contentEl.querySelector('.rv-status-text');
    if (txt) txt.textContent = isZh ? '审查完成' : 'Review complete';

    if (finalReport) {
      // 把流式收到的所有 theorem 卡塞回 final 报告，便于保存/重放
      const fullReport = Object.assign({}, finalReport, { theorem_reviews: partials });
      renderReviewSummary(contentEl.querySelector('#rv-final'), fullReport);
      const bubble = contentEl.closest('.msg-bubble');
      if (bubble) addMessageActions(bubble, JSON.stringify(fullReport, null, 2));
    }
    // 把 AI 回复内容追加到历史
    const lastHistory = AppState.history[AppState.history.length - 1];
    if (lastHistory && lastHistory.role === 'ai' && !lastHistory.content) {
      lastHistory.content = isZh ? '证明审查完成' : 'Review complete';
    }
    saveCurrentSession(isZh ? '证明审查' : 'Proof review');
    Attachments.clear();
  } catch (err) {
    if (err && err.name === 'AbortError') return;
    addErrorInline(contentEl, t('ui.err.reviewing', { e: err.message || err }));
    showToast('error', err.message || String(err));
  }
}

async function _handleReviewingPdf(attach, focusText) {
  const isZh = AppState.lang === 'zh';
  const fileName = attach.name;

  const userPreview = `📕 ${fileName}` + (focusText ? `\n\n${focusText}` : '');
  addMessage('user', userPreview);

  const contentEl = addMessage('ai', null);
  if (!contentEl) return;
  const initText = isZh ? '正在上传并解析 PDF…' : 'Uploading and parsing PDF…';
  contentEl.innerHTML = `
    <div class="review-status-pill" id="rv-status">
      <span class="spinner" aria-hidden="true"></span>
      <span class="rv-status-text">${escapeHtml(initText)}</span>
    </div>
    <div class="review-cards" id="rv-cards"></div>
    <div class="review-final" id="rv-final"></div>`;

  let finalReport = null;
  const partials = [];

  AppState.set('isStreaming', true);
  AppState._abortController = new AbortController();

  try {
    const fd = new FormData();
    fd.append('file', attach.rawFile, fileName);
    fd.append('max_theorems', String(AppState.settings.maxTheorems || 5));
    fd.append('user_id', 'anonymous');
    if (AppState.lang) fd.append('lang', AppState.lang);
    // 关键：显式走 agent 模式，否则后端默认 pipeline，无法体验 GROBID/对齐链路。
    fd.append('mode', 'agent');
    fd.append('check_logic', String(AppState.settings.checkLogic !== false));
    fd.append('check_citations', String(AppState.settings.checkCitations !== false));
    fd.append('check_symbols', String(AppState.settings.checkSymbols !== false));
    if (AppState.model) fd.append('model', AppState.model);

    const resp = await fetch('/review_pdf_stream', {
      method: 'POST',
      body: fd,
      signal: AppState._abortController.signal,
    });

    if (!resp.ok) {
      const detail = (await resp.json().catch(() => ({}))).detail || resp.statusText;
      throw new Error(detail);
    }

    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    let buf = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split('\n');
      buf = lines.pop();
      for (const raw of lines) {
        const line = raw.trim();
        if (!line.startsWith('data:')) continue;
        const body = line.slice(5).trim();
        if (!body || body === '[DONE]') continue;
        try {
          const obj = JSON.parse(body);
          if (obj.status !== undefined) {
            const txt = contentEl.querySelector('.rv-status-text');
            if (txt) txt.textContent = obj.status;
          } else if (obj.result) {
            const payload = obj.result;
            if (payload && payload.kind === 'theorem' && payload.data) {
              partials.push(payload.data);
              const cardsEl = contentEl.querySelector('#rv-cards');
              if (cardsEl) {
                cardsEl.insertAdjacentHTML('beforeend',
                  renderTheoremCardHtml(payload.data, payload.index || partials.length));
                try { renderKatexFallback(cardsEl.lastElementChild); } catch {}
                smartScroll(contentEl);
              }
            }
          } else if (obj.final) {
            finalReport = obj.final;
          } else if (obj.error) {
            throw new Error(obj.error);
          }
        } catch (parseErr) {
          if (parseErr.message && parseErr.message !== 'Unexpected token') throw parseErr;
        }
      }
    }

    const pill = contentEl.querySelector('#rv-status');
    if (pill) pill.classList.add('done');
    const txt = contentEl.querySelector('.rv-status-text');
    if (txt) txt.textContent = isZh ? '审查完成' : 'Review complete';

    if (finalReport) {
      const fullReport = Object.assign({}, finalReport, { theorem_reviews: partials });
      renderReviewSummary(contentEl.querySelector('#rv-final'), fullReport);
      const bubble = contentEl.closest('.msg-bubble');
      if (bubble) addMessageActions(bubble, JSON.stringify(fullReport, null, 2));
    }
    saveCurrentSession(isZh ? '证明审查 (PDF)' : 'Proof review (PDF)');
    Attachments.clear();
  } catch (err) {
    if (err && err.name === 'AbortError') return;
    addErrorInline(contentEl, t('ui.err.reviewing', { e: err.message || err }));
    showToast('error', err.message || String(err));
  } finally {
    AppState.set('isStreaming', false);
  }
}

async function handleSearching(query) {
  _lastAttempt = { mode: 'searching', statement: query };
  addMessage('user', query);
  const contentEl = addMessage('ai', null);
  if (contentEl) contentEl.innerHTML = makeThinkingHtml(AppState.lang === 'zh' ? '正在检索定理库…' : 'Searching theorems…');

  try {
    const data = await apiFetch('/search', { q: query, top_k: 10 });
    renderSearchResults(contentEl, data);
    const bubbleEl = contentEl?.closest('.msg-bubble');
    if (bubbleEl) addMessageActions(bubbleEl, query);
    // 把 AI 回复内容追加到历史
    const lastHistory = AppState.history[AppState.history.length - 1];
    if (lastHistory && lastHistory.role === 'ai' && !lastHistory.content) {
      lastHistory.content = `定理检索：${query}`;
    }
    saveCurrentSession(query);
  } catch (err) {
    addErrorInline(contentEl, t('ui.err.searching', { e: err.message || err }));
    showToast('error', err.message || String(err));
  }
}

function renderSearchResults(contentEl, data) {
  const results = data.results || [];
  if (!results.length) {
    contentEl.innerHTML = `<div class="search-empty">${t('ui.search.noResult')}</div>`;
    return;
  }

  const html = results.map(r => {
    const sim = r.similarity || r.score || 0;
    const simPct = Math.round(sim * 100);
    const simCls = simPct >= 80 ? 'high' : simPct >= 60 ? 'medium' : '';
    const name = r.name || r.theorem_name || '';
    const decl = r.declaration || r.lean_decl || r.body || '';
    const paper = r.paper_title || r.source || '';
    const slogan = r.slogan || '';
    const link = r.link || '';
    const authors = Array.isArray(r.paper_authors) && r.paper_authors.length
      ? r.paper_authors.slice(0, 3).join(', ') + (r.paper_authors.length > 3 ? ' et al.' : '')
      : '';

    const nameHtml = link
      ? `<a class="search-result-name-link" href="${escapeHtml(link)}" target="_blank" rel="noopener">${renderInlineMd(name)}</a>`
      : `<span>${renderInlineMd(name)}</span>`;

    const sourceHtml = (paper || link) ? `
      <div class="search-result-source">
        <span class="search-result-source-icon">↗</span>
        <span class="search-result-source-body">
          ${paper ? `<span class="search-result-paper">${renderInlineMd(paper)}</span>` : ''}
          ${authors ? `<span class="search-result-authors">${escapeHtml(authors)}</span>` : ''}
          ${link ? `<a class="search-result-link" href="${escapeHtml(link)}" target="_blank" rel="noopener">${escapeHtml(link.replace(/^https?:\/\//, '').split('/').slice(0, 3).join('/'))}</a>` : ''}
        </span>
      </div>` : '';

    return `
      <div class="search-result-item">
        <div class="search-result-header">
          <div class="search-result-name">${nameHtml}</div>
          <div class="search-result-score ${simCls}">${simPct}%</div>
        </div>
        ${slogan ? `<div class="search-result-slogan">${renderMd(slogan)}</div>` : ''}
        ${decl ? `<div class="search-result-decl lean-decl">${renderMd(decl)}</div>` : ''}
        ${sourceHtml}
      </div>`;
  }).join('');

  contentEl.innerHTML = `<div class="search-results">${html}</div>`;
  try { renderKatexFallback(contentEl); } catch {}
  contentEl.scrollIntoView({ block: 'end', behavior: 'smooth' });
}

/* ─────────────────────────────────────────────────────────────
   14. 会话保存
───────────────────────────────────────────────────────────── */
function saveCurrentSession(title) {
  const shortTitle = title.length > 30 ? title.slice(0, 29) + '…' : title;
  SessionHistory.add(shortTitle, AppState.mode, AppState.history.slice(-20));
  // 同步写入当前 project 的会话记录
  if (AppState.projectId && AppState.projectId !== 'default') {
    ProjectMemory.addSession(AppState.projectId, {
      title: shortTitle,
      mode: AppState.mode,
      ts: Date.now(),
    });
  }
}

/* ─────────────────────────────────────────────────────────────
   15. 发送
───────────────────────────────────────────────────────────── */
async function sendMessage() {
  if (AppState.isStreaming) return;

  const textarea = document.getElementById('input-textarea');
  const text = textarea?.value?.trim();

  if (!text && AppState.mode !== 'reviewing') {
    const row = textarea?.closest('.textarea-row');
    row?.classList.add('shake');
    setTimeout(() => row?.classList.remove('shake'), 500);
    return;
  }

  if (AppState.mode === 'reviewing') {
    // 预检：必须有附件或正文，不读 textarea 而是用刚才捕获的 text
    const payload = Attachments.buildPayload(text || '');
    if (!payload) {
      const ta = document.getElementById('input-textarea');
      ta?.classList.add('shake');
      setTimeout(() => ta?.classList.remove('shake'), 500);
      showToast('error', t('ui.err.emptyProof'));
      return;
    }
    if (payload.length > 50000) {
      showToast('error', t('ui.err.proofTooLong'));
      return;
    }
  }

  if (AppState.view !== 'chat') {
    AppState.set('view', 'chat');
    // plan F.3 (T52)：避免与左侧已选中的模式 tab 重复 —— title 用第一句用户输入摘要
    const titleEl = document.getElementById('chat-title');
    if (titleEl) {
      const summary = (text || '').replace(/\s+/g, ' ').trim().slice(0, 36);
      titleEl.textContent = summary || t('topbar.title') || '新对话';
    }
  }

  textarea.value = '';
  textarea.style.height = 'auto';

  switch (AppState.mode) {
    case 'learning':      await handleLearning(text);      break;
    case 'solving':       await handleSolving(text);       break;
    case 'reviewing':     await handleReviewing(text);     break;
    case 'searching':     await handleSearching(text);     break;
    case 'formalization': await handleFormalization(text); break;
  }
}

/* ─────────────────────────────────────────────────────────────
   16. 项目管理 & 结构化记忆存储
───────────────────────────────────────────────────────────── */
let _projects = [{ project_id: 'default', name: 'Default' }];
let _activeDetailProjectId = null;  // 当前详情面板显示的项目
let _editingConceptIdx = null;      // null = 新增, number = 编辑索引

// ── 结构化记忆：以 project_id 为 key 存在 localStorage ──────────────────
const ProjectMemory = {
  _key(pid) { return `vp_proj_mem_${pid}`; },
  load(pid) {
    try {
      const raw = localStorage.getItem(this._key(pid));
      return raw ? JSON.parse(raw) : { concepts: [], open_questions: [], sessions: [] };
    } catch { return { concepts: [], open_questions: [], sessions: [] }; }
  },
  save(pid, data) {
    try { localStorage.setItem(this._key(pid), JSON.stringify(data)); } catch {}
  },
  addSession(pid, { title, mode, ts }) {
    const mem = this.load(pid);
    mem.sessions = [{ title, mode, ts }, ...(mem.sessions || [])].slice(0, 30);
    this.save(pid, mem);
  },
  addOrUpdateConcept(pid, concept) {
    const mem = this.load(pid);
    const idx = mem.concepts.findIndex(c => c.name === concept.name);
    if (idx >= 0) {
      mem.concepts[idx] = { ...mem.concepts[idx], ...concept, last_reviewed: Date.now() };
    } else {
      mem.concepts.push({ ...concept, first_seen: Date.now(), last_reviewed: Date.now() });
    }
    this.save(pid, mem);
  },
  removeConcept(pid, name) {
    const mem = this.load(pid);
    mem.concepts = mem.concepts.filter(c => c.name !== name);
    this.save(pid, mem);
  },
  addQuestion(pid, q) {
    const mem = this.load(pid);
    mem.open_questions = [{ ...q, ts: Date.now() }, ...(mem.open_questions || [])];
    this.save(pid, mem);
  },
  updateQuestion(pid, idx, patch) {
    const mem = this.load(pid);
    if (mem.open_questions[idx]) mem.open_questions[idx] = { ...mem.open_questions[idx], ...patch };
    this.save(pid, mem);
  },
  removeQuestion(pid, idx) {
    const mem = this.load(pid);
    mem.open_questions.splice(idx, 1);
    this.save(pid, mem);
  },
};

const _CONCEPT_STATES = ['unseen', 'confused', 'understood', 'mastered'];
const _STATE_ICONS = { unseen: '○', confused: '◐', understood: '◑', mastered: '●' };
const _STATE_CLS   = { unseen: 'state-unseen', confused: 'state-confused', understood: 'state-understood', mastered: 'state-mastered' };

function _tState(s) {
  const map = {
    unseen: t('modal.projects.stateUnseen'),
    confused: t('modal.projects.stateConfused'),
    understood: t('modal.projects.stateUnderstood'),
    mastered: t('modal.projects.stateMastered'),
  };
  return map[s] || s;
}

async function loadProjects() {
  try {
    const data = await apiFetch('/projects', { user_id: AppState.userId });
    if (data.projects?.length) _projects = data.projects;
  } catch {}
  renderProjectList();
  // 若已有激活项目，自动打开其详情
  if (_activeDetailProjectId) {
    const still = _projects.find(p => p.project_id === _activeDetailProjectId);
    if (still) showProjectDetail(_activeDetailProjectId);
  } else if (_projects.length) {
    // 默认打开第一个项目详情
    showProjectDetail(_projects[0].project_id);
  }
}

function renderProjectList() {
  const listEl = document.getElementById('project-list');
  if (!listEl) return;
  if (!_projects.length) {
    listEl.innerHTML = `<div class="proj-empty">${t('ui.noProjects')}</div>`;
    return;
  }
  listEl.innerHTML = _projects.map(p => `
    <div class="proj-list-item ${p.project_id === AppState.projectId ? 'current' : ''} ${p.project_id === _activeDetailProjectId ? 'active' : ''}"
         data-id="${escapeHtml(p.project_id)}" data-name="${escapeHtml(p.name || p.project_id)}">
      <div class="proj-list-item-icon">${(p.name || 'P')[0].toUpperCase()}</div>
      <div class="proj-list-item-body">
        <div class="proj-list-item-name">${escapeHtml(p.name || p.project_id)}</div>
        <div class="proj-list-item-sub">${escapeHtml(p.project_id)}</div>
      </div>
      ${p.project_id === AppState.projectId ? '<span class="proj-active-badge">✓</span>' : ''}
    </div>`).join('');

  listEl.querySelectorAll('.proj-list-item').forEach(el => {
    el.addEventListener('click', () => showProjectDetail(el.dataset.id));
  });
}

function showProjectDetail(pid) {
  _activeDetailProjectId = pid;
  renderProjectList();

  const proj = _projects.find(p => p.project_id === pid);
  if (!proj) return;
  const mem = ProjectMemory.load(pid);

  document.getElementById('proj-detail-empty').style.display = 'none';
  document.getElementById('proj-create-form').style.display = 'none';
  const panel = document.getElementById('proj-detail-panel');
  panel.style.display = '';

  document.getElementById('proj-detail-name').textContent = proj.name || proj.project_id;
  document.getElementById('proj-detail-desc').textContent = proj.description || '';

  const useBtn = document.getElementById('btn-use-project');
  const indicator = document.getElementById('proj-active-indicator');
  const isActive = pid === AppState.projectId;
  if (useBtn) {
    useBtn.textContent = isActive ? (AppState.lang === 'zh' ? '已使用' : 'In use') : t('modal.projects.use');
    useBtn.disabled = isActive;
    useBtn.style.opacity = isActive ? '0.5' : '1';
  }
  if (indicator) indicator.style.display = isActive ? '' : 'none';
  useBtn.dataset.pid = pid;

  // 同步 KB constrain 开关状态
  const constrainToggle = document.getElementById('kb-constrain-toggle');
  if (constrainToggle) constrainToggle.checked = AppState.settings.kbConstrained || false;

  _renderConceptList(pid, mem.concepts || []);
  _renderKbDocList(pid);
  _renderOpenQuestions(pid, mem.open_questions || []);
  _renderSessionList(mem.sessions || []);
}

function _renderConceptList(pid, concepts) {
  const el = document.getElementById('concept-list');
  if (!el) return;
  if (!concepts.length) {
    el.innerHTML = `<div class="proj-empty-hint">${t('modal.projects.noConceptsHint')}</div>`;
    return;
  }
  el.innerHTML = concepts.map((c, i) => `
    <div class="concept-item" data-idx="${i}">
      <span class="concept-state-icon ${_STATE_CLS[c.state] || ''}" title="${_tState(c.state)}">${_STATE_ICONS[c.state] || '○'}</span>
      <div class="concept-body">
        <span class="concept-name">${escapeHtml(c.name)}</span>
        ${c.note ? `<span class="concept-note">${escapeHtml(c.note)}</span>` : ''}
      </div>
      <div class="concept-actions">
        <button class="concept-state-cycle" data-idx="${i}" title="Cycle state">↻</button>
        <button class="concept-edit" data-idx="${i}" title="Edit">✎</button>
        <button class="concept-del" data-idx="${i}" title="Remove">×</button>
      </div>
    </div>`).join('');

  el.querySelectorAll('.concept-state-cycle').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = parseInt(btn.dataset.idx);
      const mem = ProjectMemory.load(pid);
      const c = mem.concepts[idx];
      const nextIdx = (_CONCEPT_STATES.indexOf(c.state) + 1) % _CONCEPT_STATES.length;
      c.state = _CONCEPT_STATES[nextIdx];
      c.last_reviewed = Date.now();
      ProjectMemory.save(pid, mem);
      _renderConceptList(pid, mem.concepts);
    });
  });
  el.querySelectorAll('.concept-edit').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = parseInt(btn.dataset.idx);
      const mem = ProjectMemory.load(pid);
      const c = mem.concepts[idx];
      _editingConceptIdx = idx;
      document.getElementById('concept-name-input').value = c.name;
      document.getElementById('concept-state-input').value = c.state || 'unseen';
      document.getElementById('concept-note-input').value = c.note || '';
      document.getElementById('concept-modal-title').textContent = AppState.lang === 'zh' ? '编辑概念' : 'Edit Concept';
      document.getElementById('concept-modal').style.display = 'flex';
    });
  });
  el.querySelectorAll('.concept-del').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = parseInt(btn.dataset.idx);
      const mem = ProjectMemory.load(pid);
      const name = mem.concepts[idx]?.name || '';
      const msg = AppState.lang === 'zh' ? `删除概念"${name}"？` : `Remove concept "${name}"?`;
      if (confirm(msg)) {
        ProjectMemory.removeConcept(pid, name);
        _renderConceptList(pid, ProjectMemory.load(pid).concepts);
      }
    });
  });
}

function _renderOpenQuestions(pid, questions) {
  const el = document.getElementById('open-q-list');
  if (!el) return;
  if (!questions.length) {
    el.innerHTML = `<div class="proj-empty-hint">${t('modal.projects.noQuestionsHint')}</div>`;
    return;
  }
  el.innerHTML = questions.map((q, i) => `
    <div class="open-q-item ${q.status === 'answered' ? 'answered' : ''}">
      <span class="open-q-status">${q.status === 'answered' ? '✓' : '?'}</span>
      <span class="open-q-text">${escapeHtml(q.text || q.question || '')}</span>
      <div class="open-q-actions">
        ${q.status === 'open' ? `<button class="q-resolve-btn" data-idx="${i}" title="Mark answered">✓</button>` : ''}
        <button class="q-del-btn" data-idx="${i}" title="Remove">×</button>
      </div>
    </div>`).join('');

  el.querySelectorAll('.q-resolve-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      ProjectMemory.updateQuestion(pid, parseInt(btn.dataset.idx), { status: 'answered' });
      _renderOpenQuestions(pid, ProjectMemory.load(pid).open_questions);
    });
  });
  el.querySelectorAll('.q-del-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      ProjectMemory.removeQuestion(pid, parseInt(btn.dataset.idx));
      _renderOpenQuestions(pid, ProjectMemory.load(pid).open_questions);
    });
  });
}

async function _renderKbDocList(pid) {
  const el = document.getElementById('kb-doc-list');
  const dropZone = document.getElementById('kb-drop-zone');
  if (!el) return;
  el.innerHTML = `<div class="proj-empty-hint" style="opacity:.5">${AppState.lang === 'zh' ? '加载中…' : 'Loading…'}</div>`;
  try {
    const data = await apiFetch(`/projects/${encodeURIComponent(pid)}/knowledge`);
    const docs = data.documents || [];

    // 有文档时隐藏 drop zone
    if (dropZone) dropZone.style.display = docs.length ? 'none' : '';

    if (!docs.length) {
      el.innerHTML = '';
      return;
    }

    const typeIcon = (fname) => {
      const ext = fname.split('.').pop().toLowerCase();
      return { pdf: '📕', tex: '📐', md: '📝', txt: '📄', mmd: '📝' }[ext] || '📄';
    };

    el.innerHTML = docs.map(d => {
      const size = d.file_size > 1024*1024
        ? `${(d.file_size/1024/1024).toFixed(1)} MB`
        : `${Math.round(d.file_size/1024)} KB`;
      const detail = d.page_count ? `${d.page_count} pages` : `${d.chunk_count} chunks`;
      const date = new Date((d.uploaded_at||0)*1000).toLocaleDateString(
        AppState.lang === 'zh' ? 'zh-CN' : 'en-US', { month: 'short', day: 'numeric' }
      );
      return `<div class="kb-doc-item" data-doc-id="${escapeHtml(d.doc_id)}">
        <span class="kb-doc-icon">${typeIcon(d.filename)}</span>
        <div class="kb-doc-body">
          <span class="kb-doc-name" title="${escapeHtml(d.filename)}">${escapeHtml(d.filename)}</span>
          <span class="kb-doc-meta">${size} · ${detail} · ${date}</span>
        </div>
        <div class="kb-doc-actions">
          <button class="kb-doc-preview-btn" data-preview-id="${escapeHtml(d.doc_id)}" title="${t('modal.projects.kbPreview')}">⊡</button>
          <button class="kb-doc-del" data-del-id="${escapeHtml(d.doc_id)}" title="Remove">×</button>
        </div>
      </div>`;
    }).join('');

    el.querySelectorAll('.kb-doc-preview-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const did = btn.dataset.previewId;
        try {
          const data = await apiFetch(`/projects/${encodeURIComponent(pid)}/knowledge/${did}/preview`);
          _showKbPreview(data.filename, data.preview);
        } catch (e) {
          showToast('error', e.message || String(e));
        }
      });
    });
    el.querySelectorAll('.kb-doc-del').forEach(btn => {
      btn.addEventListener('click', async () => {
        const did = btn.dataset.delId;
        const msg = AppState.lang === 'zh' ? '从知识库删除此文档？' : 'Remove this document?';
        if (!confirm(msg)) return;
        try {
          await apiFetch(`/projects/${encodeURIComponent(pid)}/knowledge/${did}`, null, 'DELETE');
          _renderKbDocList(pid);
        } catch (e) {
          showToast('error', e.message || String(e));
        }
      });
    });
  } catch (e) {
    el.innerHTML = `<div class="proj-empty-hint" style="color:var(--red)">${escapeHtml(String(e))}</div>`;
  }
}

function _showKbPreview(filename, text) {
  let overlay = document.getElementById('kb-preview-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'kb-preview-overlay';
    overlay.className = 'mini-modal-overlay';
    overlay.innerHTML = `<div class="mini-modal kb-preview-modal">
      <div class="mini-modal-title" id="kb-preview-title"></div>
      <div class="kb-preview-content" id="kb-preview-content"></div>
      <button class="btn-secondary" id="kb-preview-close" style="margin-top:12px">${t('modal.projects.kbPreviewClose')}</button>
    </div>`;
    document.body.appendChild(overlay);
    overlay.querySelector('#kb-preview-close').addEventListener('click', () => {
      overlay.style.display = 'none';
    });
    overlay.addEventListener('click', e => { if (e.target === overlay) overlay.style.display = 'none'; });
  }
  overlay.querySelector('#kb-preview-title').textContent = filename;
  const contentEl = overlay.querySelector('#kb-preview-content');
  contentEl.innerHTML = renderMarkdown(text || '(empty)');
  renderKatexFallback(contentEl);
  overlay.style.display = 'flex';
}

async function _uploadKbFiles(pid, files) {
  const dropZone = document.getElementById('kb-drop-zone');
  const allowExt = /\.(pdf|txt|md|mmd|tex)$/i;

  // 并行上传，每个文件有独立的状态显示
  const uploadPromises = Array.from(files).map(async file => {
    if (!allowExt.test(file.name)) {
      showToast('error', `${file.name}: ${t('ui.err.unsupportedFile')}`);
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      showToast('error', `${file.name}: > 20 MB`);
      return;
    }

    // 在文档列表中插入上传中的占位项
    const tmpId = `tmp-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const listEl = document.getElementById('kb-doc-list');
    if (listEl) {
      const tmp = document.createElement('div');
      tmp.className = 'kb-doc-item kb-uploading';
      tmp.id = tmpId;
      tmp.innerHTML = `<span class="kb-doc-icon kb-spin">⟳</span>
        <div class="kb-doc-body">
          <span class="kb-doc-name">${escapeHtml(file.name)}</span>
          <span class="kb-doc-meta">${t('modal.projects.kbUploading')}</span>
        </div>`;
      listEl.insertBefore(tmp, listEl.firstChild);
      if (dropZone) dropZone.style.display = 'none';
    }

    const fd = new FormData();
    fd.append('file', file);
    fd.append('user_id', AppState.userId);
    try {
      const resp = await fetch(`/projects/${encodeURIComponent(pid)}/upload`, {
        method: 'POST', body: fd,
      });
      if (!resp.ok) {
        const e = await resp.json().catch(() => ({}));
        throw new Error(e.detail || `HTTP ${resp.status}`);
      }
      showToast('success', `${t('modal.projects.kbUploadOk')}: ${file.name}`);
    } catch (e) {
      showToast('error', t('modal.projects.kbUploadFail', { e: e.message || e }));
    } finally {
      document.getElementById(tmpId)?.remove();
    }
  });

  await Promise.all(uploadPromises);
  _renderKbDocList(pid);
}

function _renderSessionList(sessions) {
  const el = document.getElementById('proj-session-list');
  if (!el) return;
  if (!sessions.length) {
    el.innerHTML = `<div class="proj-empty-hint">${t('modal.projects.noSessionsHint')}</div>`;
    return;
  }
  const modeMap = { learning: 'L', solving: 'S', reviewing: 'R', searching: 'T' };
  el.innerHTML = sessions.slice(0, 10).map(s => {
    const d = new Date(s.ts || 0);
    const dateStr = d.toLocaleDateString(AppState.lang === 'zh' ? 'zh-CN' : 'en-US', { month: 'short', day: 'numeric' });
    return `<div class="proj-session-item">
      <span class="proj-session-mode hist-mode-${s.mode || 'learning'}">${modeMap[s.mode] || '?'}</span>
      <span class="proj-session-title">${escapeHtml(s.title || '')}</span>
      <span class="proj-session-date">${dateStr}</span>
    </div>`;
  }).join('');
}

async function createProject() {
  const idEl   = document.getElementById('new-project-id');
  const nameEl = document.getElementById('new-project-name');
  const descEl = document.getElementById('new-project-desc');
  if (!idEl?.value?.trim() || !nameEl?.value?.trim()) {
    showToast('error', t('ui.err.projectMissing'));
    return;
  }
  try {
    await apiPost('/projects', {
      project_id: idEl.value.trim(), name: nameEl.value.trim(),
      description: descEl?.value?.trim() || '', user_id: AppState.userId,
    });
    const newProj = { project_id: idEl.value.trim(), name: nameEl.value.trim(), description: descEl?.value?.trim() || '' };
    _projects.push(newProj);
    idEl.value = ''; nameEl.value = ''; if (descEl) descEl.value = '';
    renderProjectList();
    showToast('success', t('ui.err.projectCreated'));
    showProjectDetail(newProj.project_id);
  } catch (err) {
    showToast('error', t('ui.err.projectFailed', { e: err.message || err }));
  }
}

/* ─────────────────────────────────────────────────────────────
   17. 模态框
───────────────────────────────────────────────────────────── */
function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = 'flex';
  if (id === 'projects-modal') loadProjects();
}
function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = 'none';
}

/* ─────────────────────────────────────────────────────────────
   18. 健康检查
───────────────────────────────────────────────────────────── */
async function checkHealth() {
  const dot = document.getElementById('health-dot');
  const setStatus = (id, status) => {
    const el = document.getElementById(id);
    if (!el) return;
    const isOk = status === 'ok';
    el.textContent = status;
    el.className = `status-badge ${isOk ? 'ok' : status === '--' ? 'unknown' : 'unavailable'}`;
  };

  try {
    const data = await apiFetch('/health');
    setStatus('status-api', 'ok');
    const latraceStatus = data.dependencies?.latrace?.status || '--';
    setStatus('status-latrace', latraceStatus === 'ok' ? 'ok' : latraceStatus);
    const tsStatus = data.dependencies?.theorem_search?.status;
    setStatus('status-ts', tsStatus?.startsWith('ok') ? 'ok' : tsStatus || '--');
    if (dot) { dot.textContent = '●'; dot.className = 'health-dot online'; }
  } catch {
    setStatus('status-api', 'offline');
    if (dot) { dot.textContent = '●'; dot.className = 'health-dot offline'; }
  }
}

/* ─────────────────────────────────────────────────────────────
   19. 面板与侧栏
───────────────────────────────────────────────────────────── */
// plan H：默认折叠，必须显式打开（cursor 风格）
let _panelOpen = false;
function togglePanel(force) {
  const panelEl = document.getElementById('settings-panel');
  if (!panelEl) return;
  _panelOpen = (force !== undefined) ? force : !_panelOpen;
  panelEl.classList.toggle('open', _panelOpen);
  // plan H：管理 overlay
  let overlay = document.getElementById('settings-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'settings-overlay';
    overlay.className = 'settings-overlay';
    overlay.addEventListener('click', () => togglePanel(false));
    document.body.appendChild(overlay);
  }
  overlay.classList.toggle('open', _panelOpen);
}

let _sidebarOpen = false;
function toggleSidebar(force) {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  _sidebarOpen = (force !== undefined) ? force : !_sidebarOpen;
  sidebar?.classList.toggle('open', _sidebarOpen);
  overlay?.classList.toggle('open', _sidebarOpen);
}

/* ─────────────────────────────────────────────────────────────
   20. textarea 自动增高
───────────────────────────────────────────────────────────── */
function autoResize(textarea) {
  textarea.style.height = 'auto';
  textarea.style.height = Math.min(textarea.scrollHeight, 180) + 'px';
}

/* ─────────────────────────────────────────────────────────────
   21. 事件绑定
───────────────────────────────────────────────────────────── */
function bindEvents() {
  // toolbar LaTeX 开关按钮
  document.getElementById('toolbar-latex-btn')?.addEventListener('click', function () {
    const next = this.dataset.active !== 'true';
    this.dataset.active = String(next);
    this.setAttribute('aria-pressed', String(next));
    this.classList.toggle('active', next);
    this.title = next
      ? (AppState.lang === 'zh' ? '已开启：完成后生成 LaTeX' : 'On: generate LaTeX after solve')
      : (AppState.lang === 'zh' ? '点击开启 LaTeX 生成' : 'Click to generate LaTeX after solve');
  });

  // 卡片点击
  document.querySelectorAll('.feature-card').forEach(card => {
    const activate = () => {
      const mode = card.dataset.mode;
      const action = card.dataset.action;
      if (mode) {
        // 每次从主界面进入模块时，开启新会话（清空旧内容）
        const container = document.getElementById('chat-container');
        if (container) container.innerHTML = '';
        AppState.history = [];
        AppState.set('mode', mode);
        AppState.set('view', 'chat');
        const titleEl = document.getElementById('chat-title');
        if (titleEl) titleEl.textContent = t(`modes.${mode}`);
        document.getElementById('input-textarea')?.focus();
      } else if (action === 'open-projects') {
        openModal('projects-modal');
      } else if (action === 'open-history') {
        const sb = document.getElementById('sidebar');
        if (sb) sb.classList.add('open');
      }
    };
    card.addEventListener('click', activate);
    card.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); activate(); }
    });
  });

  // 顶部 Mode Tabs
  document.querySelectorAll('.mode-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const mode = tab.dataset.mode;
      if (mode === AppState.mode && AppState.view === 'chat') return;
      // 切换模式 = 开启新会话
      const container = document.getElementById('chat-container');
      if (container) container.innerHTML = '';
      AppState.history = [];
      AppState.set('mode', mode);
      if (AppState.view === 'chat') {
        // 已在 chat 视图：清空后展示空状态引导
        _ensureChatEmptyState();
        document.getElementById('input-textarea')?.focus();
      }
    });
  });

  document.getElementById('nav-playground')?.addEventListener('click', () => AppState.set('view', 'home'));
  document.getElementById('nav-projects')?.addEventListener('click', () => openModal('projects-modal'));
  document.getElementById('nav-health')?.addEventListener('click', () => { togglePanel(true); checkHealth(); });

  document.getElementById('hamburger')?.addEventListener('click', () => toggleSidebar());
  document.getElementById('sidebar-overlay')?.addEventListener('click', () => toggleSidebar(false));

  // plan E：返回主界面按钮
  document.getElementById('btn-home')?.addEventListener('click', () => {
    AppState.set('view', 'home');
    showToast('info', AppState.lang === 'zh' ? '已返回主界面' : 'Back to home');
  });

  document.getElementById('btn-lang-topbar')?.addEventListener('click', () => {
    const next = AppState.lang === 'zh' ? 'en' : 'zh';
    applyLang(next);
    _syncLangTopbar();
  });

  document.getElementById('btn-docs')?.addEventListener('click', () => {
    const el = document.getElementById('docs-modal');
    if (el) { _renderDocsModal(AppState.lang); el.style.display = 'flex'; }
  });
  document.getElementById('docs-modal-close')?.addEventListener('click', () => {
    document.getElementById('docs-modal').style.display = 'none';
  });
  document.getElementById('docs-modal')?.addEventListener('click', e => {
    if (e.target === document.getElementById('docs-modal'))
      document.getElementById('docs-modal').style.display = 'none';
  });

  document.getElementById('btn-panel-toggle')?.addEventListener('click', () => togglePanel());
  document.getElementById('panel-close')?.addEventListener('click', () => togglePanel(false));
  document.getElementById('btn-pin')?.addEventListener('click', () => {
    if (AppState.history.length > 0) {
      saveCurrentSession(document.getElementById('chat-title')?.textContent || 'chat');
      showToast('success', t('ui.err.savedSession'));
    } else {
      showToast('info', t('ui.err.emptyChat'));
    }
  });
  document.getElementById('btn-theme')?.addEventListener('click', toggleTheme);
  // plan H：设置面板内的语言切换
  document.getElementById('btn-lang-panel')?.addEventListener('click', () => {
    applyLang(AppState.lang === 'zh' ? 'en' : 'zh');
  });

  // plan F.3 (T51)：分段切换器（中文 / EN）
  const langSeg = document.getElementById('lang-seg');
  if (langSeg) {
    const syncSeg = () => {
      langSeg.querySelectorAll('.seg-opt').forEach(b => {
        const on = b.dataset.lang === AppState.lang;
        b.classList.toggle('active', on);
        b.setAttribute('aria-pressed', on ? 'true' : 'false');
      });
    };
    langSeg.querySelectorAll('.seg-opt').forEach(b => {
      b.addEventListener('click', () => {
        if (b.dataset.lang !== AppState.lang) {
          applyLang(b.dataset.lang);
          syncSeg();
        }
      });
    });
    syncSeg();
    // 没有 reactive subscribe — 暴露 sync 钩子，applyLang 调用结尾手动同步
    window.__syncLangSeg = syncSeg;
  }

  // 发送按钮 + 键盘
  document.getElementById('send-btn')?.addEventListener('click', sendMessage);
  document.getElementById('input-textarea')?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    if (e.key === 'Escape' && AppState.isStreaming) {
      AppState._abortController?.abort();
      AppStream.finish(`<span class="stream-stopped"> [${t('ui.stopped')}]</span>`);
    }
  });
  document.getElementById('input-textarea')?.addEventListener('input', e => autoResize(e.target));

  document.getElementById('stop-btn')?.addEventListener('click', () => {
    AppState._abortController?.abort();
    AppStream.finish(`<span class="stream-stopped"> [${t('ui.stopped')}]</span>`);
  });

  initChip('mode-chip', 'mode-dropdown', (value) => AppState.set('mode', value));
  initChip('model-chip', 'model-dropdown', (value, label) => {
    AppState.model = value;
    const chipLabel = document.getElementById('model-chip-label');
    if (chipLabel) {
      const shortName = label.split('\n').map(s => s.trim()).filter(Boolean).join(' ');
      chipLabel.textContent = shortName;
    }
    document.querySelectorAll('#model-dropdown .chip-option').forEach(li => {
      li.setAttribute('aria-selected', li.dataset.value === value ? 'true' : 'false');
    });
  });

  // 模型信息卡片（Cursor 风格：hover 显示模型介绍）
  _initModelInfoCard();

  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', () => applyLang(btn.dataset.lang));
  });

  document.getElementById('toggle-stream')?.addEventListener('change', e => { AppState.settings.stream = e.target.checked; });
  document.getElementById('toggle-memory')?.addEventListener('change', e => { AppState.settings.memoryEnabled = e.target.checked; });
  document.getElementById('toggle-extended-thinking')?.addEventListener('change', e => { AppState.settings.extendedThinking = e.target.checked; });
  document.getElementById('toggle-citation')?.addEventListener('change', e => { AppState.settings.citationCheck = e.target.checked; });
  document.getElementById('input-max-theorems')?.addEventListener('change', e => { AppState.settings.maxTheorems = parseInt(e.target.value) || 5; });
  // 审查选项
  document.getElementById('toggle-check-logic')?.addEventListener('change', e => { AppState.settings.checkLogic = e.target.checked; });
  document.getElementById('toggle-check-citations')?.addEventListener('change', e => { AppState.settings.checkCitations = e.target.checked; });
  document.getElementById('toggle-check-symbols')?.addEventListener('change', e => { AppState.settings.checkSymbols = e.target.checked; });
  document.querySelectorAll('input[name=level]').forEach(r => {
    r.addEventListener('change', e => { AppState.settings.level = e.target.value; });
  });
  // 证明附件：DeepSeek 风格回形针入口（仅 reviewing 模式下显示）
  document.getElementById('attach-btn')?.addEventListener('click', () => {
    document.getElementById('proof-file-input')?.click();
  });
  document.getElementById('proof-file-input')?.addEventListener('change', async e => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    const allowExt = /\.(pdf|tex|txt|md|mmd)$/i;
    const _MAX_TEXT_SIZE = 500 * 1024;  // 500 KB for text files
    const _MAX_PDF_SIZE  = 30 * 1024 * 1024;  // 30 MB for PDFs
    for (const file of files) {
      if (!allowExt.test(file.name)) {
        showToast('error', t('ui.err.unsupportedFile'));
        continue;
      }
      const isPdf = /\.pdf$/i.test(file.name);
      if (isPdf) {
        if (file.size > _MAX_PDF_SIZE) {
          showToast('error', AppState.lang === 'zh' ? 'PDF 超过 30 MB 上限' : 'PDF exceeds 30 MB limit');
          continue;
        }
        // Store the raw File object for direct upload to /review_pdf_stream
        Attachments.add(file, null, file);
      } else {
        if (file.size > _MAX_TEXT_SIZE) {
          showToast('error', t('ui.err.fileTooLarge'));
          continue;
        }
        try {
          const text = await file.text();
          Attachments.add(file, text);
        } catch (err) {
          showToast('error', t('ui.err.fileReadFailed', { e: err.message || err }));
        }
      }
    }
    e.target.value = '';
  });

  document.getElementById('modal-close')?.addEventListener('click', () => closeModal('projects-modal'));
  document.getElementById('projects-modal')?.addEventListener('click', e => {
    if (e.target === document.getElementById('projects-modal')) closeModal('projects-modal');
  });
  document.getElementById('btn-create-project')?.addEventListener('click', createProject);
  document.getElementById('btn-show-create-project')?.addEventListener('click', () => {
    document.getElementById('proj-detail-empty').style.display = 'none';
    document.getElementById('proj-detail-panel').style.display = 'none';
    document.getElementById('proj-create-form').style.display = '';
    _activeDetailProjectId = null;
    renderProjectList();
  });
  document.getElementById('btn-cancel-create')?.addEventListener('click', () => {
    document.getElementById('proj-create-form').style.display = 'none';
    document.getElementById('proj-detail-empty').style.display = '';
  });
  document.getElementById('btn-use-project')?.addEventListener('click', () => {
    const pid = document.getElementById('btn-use-project').dataset.pid;
    if (!pid) return;
    const proj = _projects.find(p => p.project_id === pid);
    AppState.set('projectId', pid);
    AppState.projectName = proj?.name || pid;
    showToast('success', AppState.lang === 'zh' ? `已切换到项目「${proj?.name || pid}」` : `Switched to "${proj?.name || pid}"`);
    renderProjectList();
    showProjectDetail(pid);  // 刷新详情（更新按钮状态）
  });
  // 知识库上传 + 拖拽
  document.getElementById('btn-upload-kb')?.addEventListener('click', () => {
    document.getElementById('kb-file-input')?.click();
  });
  document.getElementById('kb-file-input')?.addEventListener('change', async e => {
    const files = Array.from(e.target.files || []);
    if (!files.length || !_activeDetailProjectId) return;
    await _uploadKbFiles(_activeDetailProjectId, files);
    e.target.value = '';
  });

  // 拖拽上传
  const dropZoneEl = document.getElementById('kb-drop-zone');
  if (dropZoneEl) {
    dropZoneEl.addEventListener('click', () => document.getElementById('kb-file-input')?.click());
    dropZoneEl.addEventListener('dragover', e => { e.preventDefault(); dropZoneEl.classList.add('drag-over'); });
    dropZoneEl.addEventListener('dragleave', () => dropZoneEl.classList.remove('drag-over'));
    dropZoneEl.addEventListener('drop', async e => {
      e.preventDefault();
      dropZoneEl.classList.remove('drag-over');
      const files = Array.from(e.dataTransfer.files || []);
      if (!files.length || !_activeDetailProjectId) return;
      await _uploadKbFiles(_activeDetailProjectId, files);
    });
  }

  // 知识库约束开关
  document.getElementById('kb-constrain-toggle')?.addEventListener('change', e => {
    AppState.settings.kbConstrained = e.target.checked;
  });
  // 概念 CRUD
  document.getElementById('btn-add-concept')?.addEventListener('click', () => {
    _editingConceptIdx = null;
    document.getElementById('concept-name-input').value = '';
    document.getElementById('concept-state-input').value = 'unseen';
    document.getElementById('concept-note-input').value = '';
    document.getElementById('concept-modal-title').textContent = AppState.lang === 'zh' ? '添加概念' : 'Add Concept';
    document.getElementById('concept-modal').style.display = 'flex';
  });
  document.getElementById('btn-save-concept')?.addEventListener('click', () => {
    const name = document.getElementById('concept-name-input').value.trim();
    const state = document.getElementById('concept-state-input').value;
    const note = document.getElementById('concept-note-input').value.trim();
    if (!name) { showToast('error', AppState.lang === 'zh' ? '请输入概念名称' : 'Enter a concept name'); return; }
    const pid = _activeDetailProjectId;
    if (!pid) return;
    const mem = ProjectMemory.load(pid);
    if (_editingConceptIdx !== null) {
      mem.concepts[_editingConceptIdx] = { ...mem.concepts[_editingConceptIdx], name, state, note, last_reviewed: Date.now() };
      ProjectMemory.save(pid, mem);
    } else {
      ProjectMemory.addOrUpdateConcept(pid, { name, state, note });
    }
    document.getElementById('concept-modal').style.display = 'none';
    _renderConceptList(pid, ProjectMemory.load(pid).concepts);
  });
  document.getElementById('btn-cancel-concept')?.addEventListener('click', () => {
    document.getElementById('concept-modal').style.display = 'none';
  });
  // 问题 CRUD
  document.getElementById('btn-add-question')?.addEventListener('click', () => {
    document.getElementById('question-text-input').value = '';
    document.getElementById('question-status-input').value = 'open';
    document.getElementById('question-modal').style.display = 'flex';
  });
  document.getElementById('btn-save-question')?.addEventListener('click', () => {
    const text = document.getElementById('question-text-input').value.trim();
    const status = document.getElementById('question-status-input').value;
    if (!text) { showToast('error', AppState.lang === 'zh' ? '请输入问题' : 'Enter a question'); return; }
    const pid = _activeDetailProjectId;
    if (!pid) return;
    ProjectMemory.addQuestion(pid, { text, status });
    document.getElementById('question-modal').style.display = 'none';
    _renderOpenQuestions(pid, ProjectMemory.load(pid).open_questions);
  });
  document.getElementById('btn-cancel-question')?.addEventListener('click', () => {
    document.getElementById('question-modal').style.display = 'none';
  });

  document.addEventListener('click', () => closeAllDropdowns());

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      closeModal('projects-modal');
      closeAllDropdowns();
      if (AppState.isStreaming) {
        AppState._abortController?.abort();
        AppStream.finish(`<span class="stream-stopped"> [${t('ui.stopped')}]</span>`);
      }
    }
    if ((e.ctrlKey || e.metaKey) && e.key === '/') {
      e.preventDefault();
      document.getElementById('input-textarea')?.focus();
    }
    // Ctrl+1-4 切换模式
    if ((e.ctrlKey || e.metaKey) && /^[1-4]$/.test(e.key)) {
      e.preventDefault();
      const modes = ['learning', 'solving', 'reviewing', 'searching'];
      AppState.set('mode', modes[parseInt(e.key) - 1]);
    }
  });

  window.addEventListener('resize', () => {
    // plan H：不再根据宽度自动开关 panel，始终需要用户主动点击齿轮
    if (window.innerWidth > 768 && _sidebarOpen) toggleSidebar(false);
    _syncModeTabs();
  });

  // 监听网络状态
  window.addEventListener('offline', () => {
    showToast('warning', t('ui.err.network'), 6000);
  });
}

/* ─────────────────────────────────────────────────────────────
   22. 初始化
───────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const doInit = () => {
    applyTheme(detectTheme());
    initRenderer();
    applyLang(detectLang());
    _syncLangTopbar();
    UI.updateMode(AppState.mode);
    // plan H：默认不打开 panel（cursor 风格）
    bindEvents();
    renderExamplePrompts();
    refreshHistorySidebar();
    _syncModeTabs();
    setTimeout(checkHealth, 1200);

    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
      if (!localStorage.getItem('vp_theme')) applyTheme(e.matches ? 'dark' : 'light');
    });
  };

  if (typeof katex !== 'undefined' && typeof marked !== 'undefined') {
    doInit();
  } else {
    let tries = 0;
    const timer = setInterval(() => {
      tries++;
      if ((typeof katex !== 'undefined' && typeof marked !== 'undefined') || tries > 40) {
        clearInterval(timer); doInit();
      }
    }, 100);
  }
});
