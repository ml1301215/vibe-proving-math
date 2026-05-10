/* ═══════════════════════════════════════════════════════════════
   vibe proving — app.js  v3
   架构: AppState → UI.sync → DOM
   纯原生 JS，无构建步骤。
═══════════════════════════════════════════════════════════════ */

'use strict';

/* ─────────────────────────────────────────────────────────────
   并发控制全局锁
───────────────────────────────────────────────────────────── */
let _sendLock = false;

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
      title: 'vibe proving',
      tagline: '数学工作者的推理伙伴',
      subTagline: '严谨 · 可验证 · 不逢迎',
      examples: '示例提示词',
      hintEnter: '按', hintSend: '发送', hintNewline: '换行', hintStop: '停止',
    },
    cards: {
      learning:       { title: '学习模式', desc: '为数学命题生成分步教学讲解，面向学生' },
      solving:        { title: '问题求解', desc: '自动证明数学命题，生成完整分步证明，置信度评估与主动拒绝' },
      reviewing:      { title: '证明审查', desc: '上传数学论文 PDF，AI 将逐步审查逻辑漏洞、引用的定理与符号一致性' },
      searching:      { title: '定理检索', desc: '搜索 900 万+ 自然语言数学定理，获取定理的真实来源' },
      projects:       { title: '项目管理', desc: '保存、组织并随时回到你的研究项目' },
      history:        { title: '历史会话', desc: '浏览近期对话与提问记录，一键继续' },
      formalization:  { title: '形式化证明', desc: '直接用Aristotle吧~' },
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
      sendTip: '发送 (↵)', sendAria: '发送',
      pauseTip: '停止当前请求', pauseAria: '停止当前请求',
      aria: '输入数学命题',
      solvingPlaceholder: '输入待证命题…',
      learningPlaceholder: '输入数学命题或定理名…',
      searchingPlaceholder: '用自然语言描述定理，例如：无穷多个素数…',
    },
    panel: {
      title: '运行设置', close: '关闭',
      appearance: '外观', theme: '主题', language: '语言',
      user: '用户', logout: '退出登录', quota: '剩余次数',
      level: '学习层次', undergraduate: '本科', graduate: '研究生',
      params: '参数', stream: '流式输出', maxTheorems: '最大定理数',
      features: '功能', memory: 'LATRACE 记忆',
      citation: '引用核查', status: '服务状态',
      checkLogic: '审查逻辑漏洞', checkCitations: '核查定理引用', checkSymbols: '检查符号一致性',
      extendedThinking: '深度思考', extendedThinkingHint: '启用后模型会展示推理过程（仅 Claude）',
      shortcuts: '快捷键',
      skSend: '发送', skNewline: '换行', skStop: '停止生成',
      skFocus: '聚焦输入框', skMode: '切换模式',
      llmConfig: 'LLM API 配置', getKey: '获取 Key ↗',
      configUnknown: '未读取配置', configKeyReady: '已配置 API Key', configKeyMissing: '未配置 API Key',
      waitTips: '等待提示',
      saveLlm: '保存配置',
      nanonetsCfg: 'Nanonets PDF 解析', getNanoneetsKey: '申请 API Key ↗',
      saveNanonets: '保存',
      saving: '保存中…', saved: '已保存 ✓', saveFailed: '保存失败',
      saveFailedHint: '配置保存失败，请检查网络',
      baseUrl: 'Base URL', apiKey: 'API Key', model: 'Model',
      presetDeepseek: 'DeepSeek V4 Pro',
      presetGemini: 'Gemini 3.1 Pro',
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
      learn: {
        statusPending: '排队中',
        statusRunning: '生成中…',
        statusDone: '已完成',
        statusError: '失败',
        generatingHint: '正在生成本节…',
        generatingHintDetailed: '正在生成本节，预计 5–15 秒…',
        waitTip: '四张卡片将分阶段填充，请稍候…',
        sectionFailed: '该节生成失败：',
        retrySection: '重新生成此节',
      },
      preparing: '正在准备…',
      searchingTheorems: '正在检索定理库…',
      search: { noResult: '未找到相关定理', similarity: '相关度' },
      review: {
        overall: '整体判定',
        theorem: '定理',
        configRequired: '配置未完成',
        parseFailed: 'PDF 解析失败',
        cannotReview: '无法开始证明审查',
        configHint: '请先在右侧设置中配置对应 API Key，测试连接成功后再重新审查。',
        parseHint: '请检查 PDF 文件、网络连接或解析服务配置后重试。',
      },
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
      copy: '复制', copied: '已复制', regenerate: '重新生成', retry: '重试', stopped: '已停止',
      noHistory: '暂无历史', noProjects: '暂无项目',
      solveStarting: '启动求解…',
      solveDone: '求解完成',
      solveStopped: '已停止',
      noThumbnail: '暂无缩略图预览',
      latexGenerating: '生成中…',
      latexDone: '完成',
      latexCopied: '已复制!',
      latexError: '失败：{e}',
      latexBtnTitle: '生成可编译 LaTeX 源码',
      latexNoBlueprintHint: '暂无证明内容',
      latexOverleafHtml: '推荐使用 <a href="https://www.overleaf.com" target="_blank" rel="noopener noreferrer">Overleaf 在线编译器</a> 编译此 LaTeX 文件',
      reviewComplete: '审查完成',
      reviewConfigRequired: '配置未完成',
      reviewParseFailed: '解析失败',
      reviewIncomplete: '审查未完成（数据不完整）',
      reviewSectionProgress: '正在审查章节 {n}/{total}：{title}',
      attachFilePrefix: '--- 文件：',
      reviewFocusPrefix: '【审查重点】',
      histGroup: { today: '今天', week: '7 天内', month: '本月', older: '更早' },
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
      title: 'vibe proving — 使用指南',
      btnTitle: '使用指南',
      heroPara: '为数学工作者设计的推理伙伴。不逢迎、可验证、追求严谨。',
      modulesTitle: '核心功能',
      cards: [
        { icon: 'ℓ', title: '学习模式', body: '输入数学命题，生成结构化教学讲解：<br>• <strong>数学背景</strong>：历史脉络与实质意义<br>• <strong>完整证明</strong>：分步标注，阐明推理逻辑<br>• <strong>前置知识</strong>：理解该证明所需的概念<br>• <strong>具体例子</strong>：含边界情形与典型应用' },
        { icon: '∂', title: '问题求解', body: '输入待证命题，自动构建证明：<br>• GVR 循环：生成、验证、修订直至收敛<br>• 反例测试：检验命题可证性<br>• 置信度评估：不确定时主动拒绝' },
        { icon: '¶', title: '证明审查', body: '上传或粘贴证明文本，AI 逐步审查：<br>• 逻辑漏洞检测：gap / critical_error 标注<br>• 引用核查：TheoremSearch 验证定理真实性<br>• 符号一致性：检查变量使用与定义一致<br>• 整体判定：Correct / Partial / Incorrect' },
        { icon: '∇', title: '定理检索', body: '搜索 900 万+ 数学定理（arXiv、Stacks Project）：<br>• 自然语言查询（如 "Sylow theorem"）<br>• 返回定理陈述、来源论文、arXiv 链接<br>• 相似度排序，高质量结果优先<br>• 学习/求解模式自动调用补充上下文' },
      ],
      kbTitle: '项目管理 (Beta)',
      kbDesc: 'Project 是长期研究的组织单位。每个项目拥有独立的知识库、概念状态与开放问题，支持持续迭代研究。',
      steps: [
        { n: '1', title: '创建项目', body: '点击左侧"项目"，新建并命名你的研究项目' },
        { n: '2', title: '上传知识库', body: '添加 PDF / LaTeX / Markdown 文档作为上下文' },
        { n: '3', title: '对话与记忆', body: '所有对话自动关联项目，AI 记忆随项目持久化' },
      ],
      tip: '',
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
      title: 'vibe proving',
      tagline: 'A reasoning companion',
      subTagline: 'Rigorous · Verifiable · Honest',
      examples: 'Example prompts',
      hintEnter: 'Press', hintSend: 'to send', hintNewline: 'newline', hintStop: 'stop',
    },
    cards: {
      learning:       { title: 'Learning Mode',  desc: 'Step-by-step pedagogical explanation of math proofs' },
      solving:        { title: 'Problem Solving', desc: 'Generates complete step-by-step proofs with confidence scoring and active refusal' },
      reviewing:      { title: 'Proof Review',    desc: 'Upload a math paper PDF; AI progressively reviews logic gaps, theorem citations, and symbol consistency' },
      searching:      { title: 'Theorem Search',  desc: 'Search 9M+ math theorems in natural language and get real sources' },
      projects:       { title: 'Projects',        desc: 'Save, organize and resume your research projects' },
      history:        { title: 'History',         desc: 'Browse recent sessions and resume any conversation' },
      formalization:  { title: 'Formalization', desc: 'Just use Aristotle~' },
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
      sendTip: 'Send (↵)', sendAria: 'Send',
      pauseTip: 'Stop current request', pauseAria: 'Stop current request',
      aria: 'Math statement input',
      solvingPlaceholder: 'Enter a statement to prove…',
      learningPlaceholder: 'Enter a theorem or math concept…',
      searchingPlaceholder: 'Describe a theorem in natural language…',
    },
    panel: {
      title: 'Run settings', close: 'Close',
      appearance: 'Appearance', theme: 'Theme', language: 'Language',
      user: 'User', logout: 'Log out', quota: 'Quota',
      level: 'Level', undergraduate: 'Undergraduate', graduate: 'Graduate',
      params: 'Parameters', stream: 'Stream', maxTheorems: 'Max theorems',
      features: 'Features', memory: 'LATRACE Memory',
      citation: 'Citation check', status: 'Service',
      checkLogic: 'Check logic gaps', checkCitations: 'Verify citations', checkSymbols: 'Check symbols',
      extendedThinking: 'Extended thinking', extendedThinkingHint: 'Shows reasoning process (Claude only)',
      shortcuts: 'Shortcuts',
      skSend: 'Send', skNewline: 'Newline', skStop: 'Stop',
      skFocus: 'Focus input', skMode: 'Switch mode',
      llmConfig: 'LLM API Config', getKey: 'Get Key ↗',
      configUnknown: 'Config not loaded', configKeyReady: 'API Key configured', configKeyMissing: 'API Key missing',
      waitTips: 'Wait tips',
      saveLlm: 'Save Config',
      nanonetsCfg: 'Nanonets PDF Parsing', getNanoneetsKey: 'Apply API Key ↗',
      saveNanonets: 'Save',
      saving: 'Saving…', saved: 'Saved ✓', saveFailed: 'Save failed',
      saveFailedHint: 'Config save failed, please check your network',
      baseUrl: 'Base URL', apiKey: 'API Key', model: 'Model',
      presetDeepseek: 'DeepSeek V4 Pro',
      presetGemini: 'Gemini 3.1 Pro',
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
      learn: {
        statusPending: 'Queued',
        statusRunning: 'Generating…',
        statusDone: 'Done',
        statusError: 'Failed',
        generatingHint: 'Generating…',
        generatingHintDetailed: 'Generating this section, ~5–15s…',
        waitTip: 'Four sections will stream in sequence…',
        sectionFailed: 'This section failed:',
        retrySection: 'Regenerate this section',
      },
      preparing: 'Preparing…',
      searchingTheorems: 'Searching theorems…',
      search: { noResult: 'No theorems found', similarity: 'Similarity' },
      review: {
        overall: 'Overall verdict',
        theorem: 'Theorem',
        configRequired: 'Configuration required',
        parseFailed: 'PDF parsing failed',
        cannotReview: 'Proof review could not start',
        configHint: 'Configure the required API key in the right settings panel, test the connection, then retry the review.',
        parseHint: 'Check the PDF file, network connection, or parsing service configuration, then retry.',
      },
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
      copy: 'Copy', copied: 'Copied!', regenerate: 'Regenerate', retry: 'Retry', stopped: 'Stopped',
      noHistory: 'No history yet', noProjects: 'No projects yet',
      solveStarting: 'Starting…',
      solveDone: 'Solve complete',
      solveStopped: 'Stopped',
      noThumbnail: 'No thumbnail preview',
      latexGenerating: 'Generating…',
      latexDone: 'Done',
      latexCopied: 'Copied!',
      latexError: 'Error: {e}',
      latexBtnTitle: 'Generate compilable LaTeX',
      latexNoBlueprintHint: 'No proof content',
      latexOverleafHtml: 'Compile with <a href="https://www.overleaf.com" target="_blank" rel="noopener noreferrer">Overleaf online compiler</a>',
      reviewComplete: 'Review complete',
      reviewConfigRequired: 'Configuration required',
      reviewParseFailed: 'Parsing failed',
      reviewIncomplete: 'Review incomplete (data missing)',
      reviewSectionProgress: 'Reviewing section {n}/{total}: {title}',
      attachFilePrefix: '--- File: ',
      reviewFocusPrefix: '[Review focus] ',
      histGroup: { today: 'Today', week: 'Past 7 days', month: 'This month', older: 'Older' },
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
      title: 'vibe proving — User Guide',
      btnTitle: 'User Guide',
      heroPara: 'Rigorous · Verifiable · Honest.',
      modulesTitle: 'Four Core Modules',
      cards: [
        { icon: 'ℓ', title: 'Learning Mode', body: 'Enter any mathematical statement or theorem and AI generates:<br>• <strong>Background</strong>: historical context and significance<br>• <strong>Complete Proof</strong>: step-by-step with why at each step<br>• <strong>Examples</strong>: including boundary case analysis<br>• <strong>Further Reading</strong>: related theorems, open problems, exercises<br>• <strong>Prerequisites</strong>: concepts needed to understand the proof' },
        { icon: '∂', title: 'Problem Solving', body: 'Submit a statement to prove and AI automatically:<br>• Attempts direct proof (multi-round revision loop)<br>• Tests for counterexamples<br>• Decomposes into sub-goals<br>• Verifies citations via TheoremSearch<br>• Assigns confidence; actively refuses low-confidence results' },
        { icon: '¶', title: 'Proof Review', body: 'Paste or upload proof text (.tex/.txt/.md) and AI:<br>• Verifies each reasoning step<br>• Labels steps: passed / gap / critical_error<br>• Checks cited theorems for existence<br>• Issues overall verdict: Correct / Partial / Incorrect<br>Supports LaTeX environments (\\begin{theorem}…)' },
        { icon: '∇', title: 'Theorem Search', body: 'Search 9M+ math theorems in natural language (arXiv, Stacks Project & more):<br>• Natural language queries ("Cauchy sequence convergence")<br>• Returns theorem name, slogan, source paper, arXiv link<br>• Ranked by similarity, top results first<br>Learning/Solving modes call this automatically for context' },
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
      tip: '',
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
  UI.updateStreaming(AppState.isStreaming);
  renderExamplePrompts();
  refreshHistorySidebar();
  _renderDocsModal(lang);

  // 语言切换时如果chat-empty正在显示，重新渲染
  const chatContainer = document.getElementById('chat-container');
  if (chatContainer && chatContainer.querySelector('.chat-empty')) {
    _ensureChatEmptyState();
  }

  // 切换语言时同步模型下拉的能力标签
  document.querySelectorAll('#model-dropdown .chip-option[data-tier-zh]').forEach(li => {
    const tierEl = li.querySelector('.chip-tier');
    if (tierEl) tierEl.textContent = lang === 'zh' ? li.dataset.tierZh : li.dataset.tierEn;
  });

  // 若提示条正在显示，立即切换为新语言内容
  const tipEl = _waitTipEl || document.querySelector('[data-wait-tip="true"]');
  if (tipEl) {
    const tips = _WAIT_TIPS[lang] || _WAIT_TIPS.en;
    const txtEl = tipEl.querySelector('.wait-tip-text');
    if (txtEl) {
      tipEl.classList.remove('visible');
      setTimeout(() => {
        txtEl.innerHTML = _renderWaitTipText(tips[_waitTipIdx % tips.length]);
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
  const tipSection = d.tip ? `<div class="docs-section docs-tip"><strong>${tipLabel}：</strong>${d.tip}</div>` : '';
  body.innerHTML =
    `<div class="docs-hero"><h2>vibe proving</h2><p>${d.heroPara}</p></div>` +
    `<div class="docs-section"><h3>${d.modulesTitle}</h3><div class="docs-grid">${cards}</div></div>` +
    `<div class="docs-section"><h3>${d.kbTitle}</h3><p>${d.kbDesc}</p><div class="docs-steps">${steps}</div></div>` +
    tipSection;
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

  // 统一类型别名：warn → warning，避免 CSS 类名不一致
  if (type === 'warn') type = 'warning';
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
  if (typeof marked === 'undefined') return;

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
  // 末尾用 (?!\[a-zA-Z]) 替代 \b，使 \chi_\sigma 这类「命令+下标」也能被包进 $...$
  s = s.replace(/(?<![\\$\w])(\\(?:frac|sqrt|sum|prod|int|lim|sup|inf|mathbb|mathcal|mathfrak|mathrm|mathbf|mathit|operatorname|forall|exists|in|notin|subset|subseteq|cup|cap|leq|geq|neq|to|mapsto|Rightarrow|Leftrightarrow|alpha|beta|gamma|delta|epsilon|varepsilon|zeta|eta|theta|vartheta|iota|kappa|lambda|mu|nu|xi|pi|rho|sigma|tau|upsilon|phi|varphi|chi|psi|omega|Gamma|Delta|Theta|Lambda|Xi|Pi|Sigma|Phi|Psi|Omega|infty|partial|nabla|cdot|cdots|ldots|times|div|pm|mp|approx|equiv|sim|propto|circ|prime)(?:\{[^{}]*\}|(?![a-zA-Z])))/g,
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
  seg = normalizeEscapedNewlines(seg);
  if (_MD_CACHE.has(seg)) return _MD_CACHE.get(seg);
  let html;
  try {
    html = typeof marked !== 'undefined'
      ? marked.parse(preRenderDisplayMath(autoWrapMath(seg)))
      : `<p>${escapeHtml(seg).replace(/\n/g, '<br>')}</p>`;
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
  return _renderOneSegment(normalizeEscapedNewlines(text));
}

/** 流式 Markdown：把 text 按 \n\n 切段，已完成段走缓存，只重做最后一段。 */
function renderStreamingMarkdown(text) {
  if (!text) return '';
  text = normalizeEscapedNewlines(text);
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
        out += marked.parse(preRenderDisplayMath(autoWrapMath(p)));
      } catch {
        out += `<pre>${escapeHtml(p)}</pre>`;
      }
    } else {
      out += _renderOneSegment(p);
    }
  }
  return out;
}

function normalizeEscapedNewlines(text) {
  if (text === null || text === undefined) return '';
  let s = String(text);
  if (!s.includes('\\n')) return s;

  // Handle doubled escaping from JSON-ish payloads before single-backslash cases.
  s = s.replace(/\\\\n(?=\s*(?:[A-Za-z](?:[_^]|\s*\^)|[A-Z]\s*(?:[=+\-*/^_]|\\(?:in|cup|sqcup|subset|subseteq|le|leq|ge|geq))|\\(?:sum|prod|int|frac|sqrt|lim|begin|end|mathbf|mathbb|mathcal|mathrm)))/g, '');
  s = s.replace(/\\\\n(?=(?:\s|$|[#>*\-+0-9`$|]|[A-Z][a-z]|Step\b|Then\b|This\b|For\b|If\b|We\b|Now\b))/g, '\n');

  // Fix malformed math fragments like `\nx^T Lx` or `\nV = ...` inside display math.
  s = s.replace(/\\n(?=\s*(?:[A-Za-z](?:[_^]|\s*\^)|[A-Z]\s*(?:[=+\-*/^_]|\\(?:in|cup|sqcup|subset|subseteq|le|leq|ge|geq))|\\(?:sum|prod|int|frac|sqrt|lim|begin|end|mathbf|mathbb|mathcal|mathrm)))/g, '');

  // Convert literal newline escapes that are clearly prose / Markdown separators.
  s = s.replace(/\\n(?=(?:\s|$|[#>*\-+0-9`$|]|[A-Z][a-z]|Step\b|Then\b|This\b|For\b|If\b|We\b|Now\b))/g, '\n');

  // Clean up newline escapes that land immediately after sentence punctuation.
  s = s.replace(/([.!?。；;:])\\n(?=\S)/g, '$1\n');
  return s;
}

function preRenderDisplayMath(text) {
  if (!text || typeof katex === 'undefined') return text;
  const renderDisplay = (raw, expr) => {
    try {
      return `\n\n<div class="katex-display">${katex.renderToString(expr.trim(), {
        displayMode: true,
        throwOnError: false,
        output: 'html',
      })}</div>\n\n`;
    } catch {
      return raw;
    }
  };
  return text
    .replace(/\$\$([\s\S]*?)\$\$/g, renderDisplay)
    .replace(/\\\[([\s\S]*?)\\\]/g, renderDisplay);
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
  config: null,
  user: null,
  userId: '',
  settings: {
    level: 'undergraduate',
    maxTheorems: 5,
    waitTips: localStorage.getItem('vp_wait_tips') !== '0',
    attachments: [],   // [{name, size, content}]
    kbConstrained: false,  // 仅在知识库范围内回答
    // 审查选项
    checkLogic: true,      // 审查逻辑漏洞
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
   5.1 PDF.js 懒加载 & PDF 元数据读取
───────────────────────────────────────────────────────────── */
const _PDFJS_VERSION = '3.11.174';
let _pdfJsReady = null;

function _ensurePdfJs() {
  if (_pdfJsReady) return _pdfJsReady;
  _pdfJsReady = new Promise((resolve, reject) => {
    if (window.pdfjsLib) { resolve(window.pdfjsLib); return; }
    const s = document.createElement('script');
    s.src = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${_PDFJS_VERSION}/pdf.min.js`;
    s.onload = () => {
      window.pdfjsLib.GlobalWorkerOptions.workerSrc =
        `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${_PDFJS_VERSION}/pdf.worker.min.js`;
      resolve(window.pdfjsLib);
    };
    s.onerror = (err) => { _pdfJsReady = null; reject(err); };
    document.head.appendChild(s);
  });
  return _pdfJsReady;
}

async function _loadPdfMeta(file, attachment) {
  try {
    const pdfjs = await _ensurePdfJs();
    const buf = await file.arrayBuffer();
    const pdf = await pdfjs.getDocument({ data: buf }).promise;
    attachment.pageCount = pdf.numPages;

    const thumbCount = Math.min(3, pdf.numPages);
    const thumbnails = [];
    for (let i = 1; i <= thumbCount; i++) {
      const page = await pdf.getPage(i);
      const viewport = page.getViewport({ scale: 0.35 });
      const canvas = document.createElement('canvas');
      canvas.width = Math.round(viewport.width);
      canvas.height = Math.round(viewport.height);
      const ctx = canvas.getContext('2d');
      await page.render({ canvasContext: ctx, viewport }).promise;
      thumbnails.push(canvas.toDataURL('image/jpeg', 0.7));
    }
    attachment.thumbnails = thumbnails;
    pdf.destroy();
  } catch (e) {
    console.warn('[PDF.js] meta load failed:', e);
    attachment.pageCount = null;
    attachment.thumbnails = [];
  }
  Attachments.render();
}

/* ─────────────────────────────────────────────────────────────
   5.2 PDF 缩略图 Tooltip
───────────────────────────────────────────────────────────── */
let _thumbTooltipEl = null;
let _hideTooltipTimer = null;
let _tooltipChipEl = null;  // 当前触发 tooltip 的 chip 元素

function _tooltipDocMouseover(e) {
  // 鼠标移到 chip 或 tooltip 以外的元素时立即关闭
  if (!_thumbTooltipEl) return;
  if (
    (_tooltipChipEl && _tooltipChipEl.contains(e.target)) ||
    _thumbTooltipEl.contains(e.target)
  ) return;
  _hidePdfThumbTooltipNow();
}

function _showPdfThumbTooltip(chipEl, thumbnails) {
  if (_hideTooltipTimer) { clearTimeout(_hideTooltipTimer); _hideTooltipTimer = null; }
  _hidePdfThumbTooltipNow();
  if (!thumbnails?.length) return;

  _tooltipChipEl = chipEl;
  const tooltip = document.createElement('div');
  tooltip.className = 'pdf-thumb-tooltip';
  tooltip.innerHTML = thumbnails.map(src =>
    `<img class="pdf-thumb-img" src="${src}" alt="">`
  ).join('');
  document.body.appendChild(tooltip);
  _thumbTooltipEl = tooltip;

  // 全局兜底：鼠标移到 chip/tooltip 之外立即关闭
  document.addEventListener('mouseover', _tooltipDocMouseover, { capture: true });
  // 滚动时关闭（scroll 发生后 chip 位置已变）
  window.addEventListener('scroll', _hidePdfThumbTooltipNow, { capture: true, once: true });

  requestAnimationFrame(() => {
    const rect = chipEl.getBoundingClientRect();
    const ttH = tooltip.offsetHeight || 134;
    const ttW = tooltip.offsetWidth || (thumbnails.length * 88 + 22);
    let top = rect.top - ttH - 8;
    if (top < 8) top = rect.bottom + 8;
    let left = rect.left;
    if (left + ttW > window.innerWidth - 8) left = window.innerWidth - ttW - 8;
    if (left < 8) left = 8;
    tooltip.style.top = `${top}px`;
    tooltip.style.left = `${left}px`;
    tooltip.style.opacity = '1';
  });
}

function _hidePdfThumbTooltip() {
  if (_hideTooltipTimer) clearTimeout(_hideTooltipTimer);
  _hideTooltipTimer = setTimeout(_hidePdfThumbTooltipNow, 150);
}

function _hidePdfThumbTooltipNow() {
  if (_thumbTooltipEl) { _thumbTooltipEl.remove(); _thumbTooltipEl = null; }
  _tooltipChipEl = null;
  _hideTooltipTimer = null;
  // 清理全局监听器
  document.removeEventListener('mouseover', _tooltipDocMouseover, { capture: true });
  window.removeEventListener('scroll', _hidePdfThumbTooltipNow, { capture: true });
}

/* ─────────────────────────────────────────────────────────────
   5.3 PDF 全屏查看器
───────────────────────────────────────────────────────────── */
let _viewerEscHandler = null;

function openPdfViewer(url, name, pageCount) {
  const modal = document.getElementById('pdf-viewer-modal');
  if (!modal) return;
  const titleEl = document.getElementById('pdf-viewer-title');
  const pagesEl = document.getElementById('pdf-viewer-pages');
  const iframe = document.getElementById('pdf-viewer-iframe');
  if (titleEl) titleEl.textContent = name || '';
  if (pagesEl) pagesEl.textContent = pageCount ? `${pageCount} 页` : '';
  if (iframe) iframe.src = url;
  modal.style.display = 'flex';

  if (_viewerEscHandler) document.removeEventListener('keydown', _viewerEscHandler);
  _viewerEscHandler = (e) => { if (e.key === 'Escape') closePdfViewer(); };
  document.addEventListener('keydown', _viewerEscHandler);
}

function closePdfViewer() {
  if (_viewerEscHandler) { document.removeEventListener('keydown', _viewerEscHandler); _viewerEscHandler = null; }
  const modal = document.getElementById('pdf-viewer-modal');
  if (!modal) return;
  const iframe = document.getElementById('pdf-viewer-iframe');
  if (iframe) iframe.src = '';
  modal.style.display = 'none';
}

/* ─────────────────────────────────────────────────────────────
   5.3b PDF 缩略图画廊（聊天气泡点击后弹出）
───────────────────────────────────────────────────────────── */
let _galleryEscHandler = null;

function openPdfGallery(thumbnails, name, pageCount, objectUrl) {
  const modal = document.getElementById('pdf-gallery-modal');
  if (!modal) return;

  const titleEl = document.getElementById('pdf-gallery-title');
  const pagesEl = document.getElementById('pdf-gallery-pages');
  const bodyEl  = document.getElementById('pdf-gallery-body');
  const footerEl = document.getElementById('pdf-gallery-footer');

  if (titleEl) titleEl.textContent = name || '';
  if (pagesEl) pagesEl.textContent = pageCount ? `${pageCount} 页` : '';

  if (bodyEl) {
    if (thumbnails && thumbnails.length) {
      bodyEl.innerHTML = thumbnails.map((src, i) => `
        <div class="pdf-gallery-img-wrap">
          <img class="pdf-gallery-img" src="${src}" alt="第 ${i + 1} 页">
          <div class="pdf-gallery-img-label">第 ${i + 1} 页</div>
        </div>`).join('');
    } else {
      bodyEl.innerHTML = `<p style="color:var(--text-muted);padding:20px;">${t('ui.noThumbnail')}</p>`;
    }
  }

  if (footerEl) {
    footerEl.innerHTML = objectUrl
      ? `<button class="pdf-gallery-open-btn" onclick="openPdfViewer('${objectUrl}','${(name||'').replace(/'/g,"\\'")}',${pageCount||0})">在全屏查看器中打开</button>`
      : '';
    footerEl.style.display = objectUrl ? '' : 'none';
  }

  modal.style.display = 'flex';

  if (_galleryEscHandler) document.removeEventListener('keydown', _galleryEscHandler);
  _galleryEscHandler = (e) => { if (e.key === 'Escape') closePdfGallery(); };
  document.addEventListener('keydown', _galleryEscHandler);
}

function closePdfGallery() {
  if (_galleryEscHandler) { document.removeEventListener('keydown', _galleryEscHandler); _galleryEscHandler = null; }
  const modal = document.getElementById('pdf-gallery-modal');
  if (modal) modal.style.display = 'none';
}

/* ─────────────────────────────────────────────────────────────
   5.4 附件管理（DeepSeek 风格 chip）
───────────────────────────────────────────────────────────── */
const Attachments = {
  add(file, content, rawFile) {
    const isPdf = /\.pdf$/i.test(file.name);
    const att = {
      name: file.name,
      size: file.size,
      content,
      rawFile: rawFile || null,
      pageCount: null,
      objectUrl: (isPdf && rawFile) ? URL.createObjectURL(rawFile) : null,
      thumbnails: [],
    };
    AppState.settings.attachments.push(att);
    this.render();
    updateInputPlaceholder();
    if (isPdf && rawFile) _loadPdfMeta(rawFile, att);
  },
  remove(idx) {
    const att = AppState.settings.attachments[idx];
    if (att?.objectUrl) URL.revokeObjectURL(att.objectUrl);
    AppState.settings.attachments.splice(idx, 1);
    this.render();
    updateInputPlaceholder();
  },
  clear() {
    (AppState.settings.attachments || []).forEach(att => {
      if (att?.objectUrl) URL.revokeObjectURL(att.objectUrl);
    });
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
      const isPdf = /\.pdf$/i.test(a.name);
      const icon = isPdf ? '📕' : '📎';
      const pageStr = (isPdf && a.pageCount) ? ` · ${a.pageCount} 页` : '';
      const meta = a.rawFile
        ? `${(a.size / 1024 / 1024).toFixed(1)}MB${pageStr}`
        : `${(a.size / 1024).toFixed(1)}KB`;
      const clickable = isPdf && a.objectUrl ? ' data-pdf-open="1"' : '';
      return `
      <div class="attachment-chip${isPdf ? ' is-pdf' : ''}" data-idx="${i}"${clickable}>
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

    el.querySelectorAll('.is-pdf[data-pdf-open]').forEach(chip => {
      chip.addEventListener('click', () => {
        const idx = parseInt(chip.dataset.idx, 10);
        if (!Number.isFinite(idx)) return;
        const att = (AppState.settings.attachments || [])[idx];
        if (att?.objectUrl) openPdfViewer(att.objectUrl, att.name, att.pageCount);
      });
    });

    el.querySelectorAll('.is-pdf').forEach(chip => {
      chip.addEventListener('mouseenter', () => {
        const idx = parseInt(chip.dataset.idx, 10);
        if (!Number.isFinite(idx)) return;
        const att = (AppState.settings.attachments || [])[idx];
        if (att?.thumbnails?.length) _showPdfThumbTooltip(chip, att.thumbnails);
      });
      chip.addEventListener('mouseleave', _hidePdfThumbTooltip);
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
      .map(a => `${t('ui.attachFilePrefix')}${a.name} ---\n${a.content}`)
      .join('\n\n');
    const focus = userMsg ? `\n\n${t('ui.reviewFocusPrefix')}\n${userMsg}` : '';
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
  _sessions: [],
  load() {
    return this._sessions || [];
  },
  save(sessions) { this._sessions = (sessions || []).slice(0, 50); },
  async sync() {
    try {
      const data = await apiFetch('/history');
      this._sessions = data.sessions || [];
    } catch {
      this._sessions = [];
    }
    refreshHistorySidebar();
  },
  add(title, mode, messages) {
    const temp = { id: Date.now(), title, mode, ts: Date.now(), messages };
    this._sessions = [temp, ...this.load()].slice(0, 50);
    refreshHistorySidebar();
    apiPost('/history', { title, mode, messages })
      .then(data => {
        if (data.session) {
          this._sessions = [data.session, ...this.load().filter(s => s.id !== temp.id)].slice(0, 50);
          refreshHistorySidebar();
        }
      })
      .catch(err => console.warn('history save failed', err));
  },
  // plan E：删除单条历史
  remove(id) {
    const sessions = this.load().filter(s => s.id !== id);
    this.save(sessions);
    refreshHistorySidebar();
    fetch(`${API_BASE}/history/${encodeURIComponent(id)}`, { method: 'DELETE' }).catch(() => {});
  },
  clear() {
    this._sessions = [];
    refreshHistorySidebar();
    fetch(`${API_BASE}/history`, { method: 'DELETE' }).catch(() => {});
  }
};

function _historyGroup(ts) {
  // 按时间分组：今天 / 7 天内 / 更早
  const now = Date.now();
  const oneDay = 24 * 60 * 60 * 1000;
  const dayDiff = Math.floor((now - ts) / oneDay);
  if (dayDiff < 1) return t('ui.histGroup.today');
  if (dayDiff < 7) return t('ui.histGroup.week');
  if (dayDiff < 30) return t('ui.histGroup.month');
  return t('ui.histGroup.older');
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
  const modeMap = { learning: 'L', solving: 'S', reviewing: 'R', searching: 'T', formalization: 'F' };
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
  (session.messages || []).forEach(msg => addMessage(msg.role, msg.content, {
    noSave: true,
    pdfAttachments: msg.pdfAttachments,
  }));
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
        { label: 'Lemma 2.1（共轭类整除性证明）', text: '**引理 2.1**（消失元论文，§2）\n设 $G$ 是有限群，$N$ 是 $G$ 的正规子群。则：\n(i) 对任意 $x \\in N$，$|x^N|$ 整除 $|x^G|$；\n(ii) 对任意 $g \\in G$，$|(gN)^{G/N}|$ 整除 $|g^G|$。\n\n**证明**：\n(i) 由共轭类-稳定子定理，$|x^N| = [N : C_N(x)]$ 且 $|x^G| = [G : C_G(x)]$。由于 $C_N(x) = N \\cap C_G(x)$，而 $[G : C_G(x)] = [G : N C_G(x)] \\cdot [N C_G(x) : C_G(x)]$，结合 $[N C_G(x) : C_G(x)] = [N : N \\cap C_G(x)] = [N : C_N(x)]$，得 $|x^N|$ 整除 $|x^G|$。\n\n(ii) 由第一同构定理，$|(gN)^{G/N}| = [G/N : C_{G/N}(gN)]$。注意 $C_{G/N}(gN) \\supseteq C_G(g)N/N$，故 $|(gN)^{G/N}|$ 整除 $[G : C_G(g)N] \\leq [G : C_G(g)] = |g^G|$。$\\square$' },
        { label: '📄 PDF 工作流示例：消失元论文（arXiv:2501.13605）', text: '__pdf__:/ui/examples/vanishing_elements_2501.13605.pdf' },
      ],
      en: [
        { label: 'Lemma 2.1 (conjugacy class divisibility)', text: '**Lemma 2.1** (vanishing elements paper, §2)\nLet $G$ be a finite group and $N$ a normal subgroup of $G$. Then:\n(i) For any $x \\in N$, $|x^N|$ divides $|x^G|$;\n(ii) For any $g \\in G$, $|(gN)^{G/N}|$ divides $|g^G|$.\n\n**Proof**:\n(i) By the orbit-stabilizer theorem, $|x^N| = [N : C_N(x)]$ and $|x^G| = [G : C_G(x)]$. Since $C_N(x) = N \\cap C_G(x)$, and $[G : C_G(x)] = [G : NC_G(x)] \\cdot [NC_G(x) : C_G(x)]$ with $[NC_G(x) : C_G(x)] = [N : C_N(x)]$, we get $|x^N|$ divides $|x^G|$.\n\n(ii) By the first isomorphism theorem, $|(gN)^{G/N}| = [G/N : C_{G/N}(gN)]$. Since $C_{G/N}(gN) \\supseteq C_G(g)N/N$, we have $|(gN)^{G/N}|$ divides $[G : C_G(g)] = |g^G|$. $\\square$' },
        { label: '📄 PDF workflow example: vanishing elements paper (arXiv:2501.13605)', text: '__pdf__:/ui/examples/vanishing_elements_2501.13605.pdf' },
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
    el.addEventListener('click', async () => {
      const raw = el.dataset.raw || '';
      // PDF 工作流示例：自动 fetch 并挂载为附件
      if (raw.startsWith('__pdf__:')) {
        const url = raw.slice('__pdf__:'.length);
        const filename = url.split('/').pop() || 'example.pdf';
        try {
          const resp = await fetch(url);
          if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
          const blob = await resp.blob();
          const file = new File([blob], filename, { type: 'application/pdf' });
          Attachments.clear();
          Attachments.add(file, null, file);
          AppState.set('mode', 'reviewing');
          showToast('success', AppState.lang === 'zh'
            ? `已加载 ${filename}，点击发送开始审查`
            : `Loaded ${filename} — click send to start review`);
        } catch (err) {
          showToast('error', AppState.lang === 'zh'
            ? `PDF 加载失败: ${err.message}`
            : `Failed to load PDF: ${err.message}`);
        }
        return;
      }
      // 普通文本示例
      const ta = document.getElementById('input-textarea');
      if (ta) {
        ta.value = raw || el.textContent || '';
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
    const inputBar = document.getElementById('input-bar');
    const chipRow = document.querySelector('.chip-row');
    const examplePrompts = document.getElementById('example-prompts');
    if (!homeEl || !chatEl) return;
    if (view === 'home') {
      homeEl.style.display = '';
      chatEl.style.display = 'none';
      navHome && navHome.classList.add('active');
      if (btnHome) btnHome.style.display = 'none';
      if (btnPin)  btnPin.style.display  = 'none';
      if (inputBar) inputBar.style.display = 'none';
      if (examplePrompts) examplePrompts.style.display = 'none';
    } else {
      homeEl.style.display = 'none';
      chatEl.style.display = '';
      navHome && navHome.classList.remove('active');
      if (btnHome) btnHome.style.display = '';
      if (btnPin)  btnPin.style.display  = '';
      if (inputBar) inputBar.style.display = '';
      if (chipRow) chipRow.style.display = 'none';
      if (examplePrompts) examplePrompts.style.display = 'none';
      _ensureChatEmptyState();
    }
  },

  updateMode(mode) {
    const isReview = mode === 'reviewing';
    const isSolving = mode === 'solving';
    const attachBtn = document.getElementById('attach-btn');
    if (attachBtn) attachBtn.style.display = isReview ? '' : 'none';
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
    const configuredModel = AppState.config?.llm?.model;
    const defaultModel = configuredModel || _MODE_MODELS[mode] || 'gemini-2.5-flash';
    setActiveModel(defaultModel);

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
    if (sendBtn) _setSendButtonMode(!!isStreaming);
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
  const keyMap = {
    learning:  'input.learningPlaceholder',
    solving:   'input.solvingPlaceholder',
    searching: 'input.searchingPlaceholder',
  };
  ta.placeholder = keyMap[AppState.mode] ? t(keyMap[AppState.mode]) : t('input.placeholder');
}

const MODEL_LABELS = {
  'gemini-2.5-flash': 'Gemini 2.5 Flash',
  'gemini-2.5-pro': 'Gemini 2.5 Pro',
  'gemini-3.1-pro-preview': 'Gemini 3.1 Pro',
  'gpt-5.3-codex': 'GPT 5.3 Codex',
  'gpt-5.4': 'GPT 5.4',
  'gpt-5': 'GPT-5',
  'gpt-4o': 'GPT-4o',
  'claude-sonnet-4-6': 'Claude Sonnet 4.6',
  'claude-opus-4-7': 'Claude Opus 4.7',
  'o3': 'o3',
  'o4-mini': 'o4-mini',
  'kimi-k2.6': 'Kimi K2.6',
  'deepseek-v4-pro': 'DeepSeek V4 Pro',
  'deepseek-v4-flash': 'DeepSeek V4 Flash',
  'deepseek-chat': 'DeepSeek Chat',
};

function setActiveModel(model, label) {
  const value = (model || '').trim();
  if (!value) return;
  AppState.model = value;
  const chipLabel = document.getElementById('model-chip-label');
  if (chipLabel) chipLabel.textContent = label || MODEL_LABELS[value] || value;
  document.querySelectorAll('#model-dropdown .chip-option').forEach(li => {
    li.setAttribute('aria-selected', li.dataset.value === value ? 'true' : 'false');
  });
}

function _setSendButtonMode(isStreaming) {
  const sendBtn = document.getElementById('send-btn');
  if (!sendBtn) return;
  const sendIcon = '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M5 12l14-7-7 14-2-5-5-2z"/></svg>';
  const pauseIcon = '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z"/></svg>';
  sendBtn.disabled = false;
  sendBtn.innerHTML = isStreaming ? pauseIcon : sendIcon;
  sendBtn.dataset.tooltip = isStreaming ? t('input.pauseTip') : t('input.sendTip');
  sendBtn.setAttribute('aria-label', isStreaming ? t('input.pauseAria') : t('input.sendAria'));
}

function stopActiveRun({ markStream = true } = {}) {
  if (!AppState.isStreaming) return;
  try { AppState._abortController?.abort(); } catch {}
  stopWaitTips();
  _stopReviewWaitTips(null);
  if (markStream && AppStream.msgEl) {
    AppStream.finish(`<span class="stream-stopped"> [${t('ui.stopped')}]</span>`);
  }
  AppState.set('isStreaming', false);
  _sendLock = false;
}

function _cancelActiveRunForModeSwitch() {
  stopActiveRun({ markStream: true });
}

function switchMode(mode, opts = {}) {
  if (!mode) return;
  if (mode === 'formalization') {
    window.open('https://aristotle.harmonic.fun/dashboard', '_blank', 'noopener');
    return;
  }
  if (mode === AppState.mode && AppState.view === 'chat' && !opts.force) return;
  _cancelActiveRunForModeSwitch();

  if (opts.resetChat !== false) {
    const container = document.getElementById('chat-container');
    if (container) container.innerHTML = '';
    AppState.history = [];
  }

  AppState.set('mode', mode);
  AppState.set('view', 'chat');
  const titleEl = document.getElementById('chat-title');
  if (titleEl) titleEl.textContent = t(`modes.${mode}`);
  _ensureChatEmptyState();
  document.getElementById('input-textarea')?.focus();
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
    // ── 功能介绍 ──
    '"问题求解"模式，专门针对研究级别的数学问题',
    '定理检索可以从 900 万+ 定理库中找到定理的论文来源和作者',
    '在"证明审查"模式中上传论文 PDF，AI 会逐步独立核验论文中每个推理步骤的合法性',
    '在 Project 中上传数学文献 PDF，AI 的回答将优先参考你的知识库内容',
    '"证明审查"支持上传 .tex / .md 文件，可以直接审查你的 LaTeX 论文草稿',
    '上传整本教材后，在"学习模式"提问时，AI 会优先参考你上传的书中内容来回答',
    '在 Project 里记录"开放问题"，下次打开时可以无缝接续上次的探索',
    '将一段你不确定的证明粘贴进"证明审查"，AI 会指出每个有问题的步骤并说明原因',
    // ── 使用技巧 ──
    '求解完成后，悬停在 AI 回复气泡上，操作行会显示 { } LaTeX 按钮——点击即可生成可编译的 LaTeX 源码',
    '"学习模式"生成四节内容时，可以单独点击某节标题旁的"重新生成"按钮，无需重跑整个流程',
    '若某个定理名出现在证明中但你不确定其内容，直接在"定理检索"里粘贴这个名字，通常能立刻找到来源',
    '知识库上传的 PDF 建议保持在 5MB 以下，过大的 PDF 可以先用 pdfcrop 或 ghostscript 拆分成章节再上传',
    '模型下拉中"DeepSeek V4 Pro"经济实惠适合大量迭代验证，"Gemini 3.1 Pro"推理能力更强适合复杂问题的探索',
    '问题求解的结果页右侧会出现 LaTeX 面板——点击复制后直接粘贴进 Overleaf 即可完整编译',
    '历史会话自动保存在本地浏览器；同一问题的多次尝试会作为独立会话保存，方便对比不同证明路径',
    '如果证明被系统"主动拒绝"（置信度极低），往往意味着命题条件有遗漏，或者是经典开放问题，可去"定理检索"验证',
    '复杂问题先拆成 2 到 3 个引理分别提问，通常比一次要求完整证明更容易得到稳定结果',
    '切换模型下拉，可以选择不同的 AI 来处理同一个命题，比较它们证明风格的差异',
    '如果一个命题总是证明不顺，先去"定理检索"里查标准名称、经典等价形式或已知特例，通常能更快找到突破口',
    '如果你在写论文，可以先让 AI 给出证明蓝图，再把关键步骤改写成你自己的记号和叙述风格',
    '很多看似正确的命题其实只差一个条件；当系统给出反例时，最值得关注的是它暴露了哪个隐藏假设',
    '进度条到达 100% 只代表服务器处理完成；复杂 PDF 可能需要数分钟，等待时可以翻看等待提示里的数学趣闻',
    '在项目管理里记录每个概念的学习状态（未接触→有疑惑→已理解→已掌握），相当于搭建个人知识图谱',
    '学习模式输出的"前置知识"节，帮助你快速判断当前命题依赖哪些已知概念，适合查漏补缺',
    '证明审查提示"gap"的步骤，往往是逻辑跳跃最大的地方——那里通常需要补写一个引理',
    '对于涉及分析或测度论的命题，试着先让 AI 给出直觉解释，再要求严格 $\\epsilon$-$\\delta$ 证明',
    '使用"定理检索"时，描述尽量具体：加上字段名、边界条件或等价说法，准确率会大幅提升',
    // ── 经典结论与数学趣味 ──
    '欧拉恒等式 $e^{i\\pi}+1=0$ 将 $e$、$i$、$\\pi$、$1$、$0$ 五个最重要的数字统一在一个等式里，被许多数学家票选为"最美公式"',
    '素数有无穷多个——欧几里得的证明只用了五行，2300 年后没人找到更短的',
    '$\\sqrt{2}$ 是无理数的证明出自古希腊，但据说最先证明这件事的人因此被扔进了海里',
    '黎曼猜想说 $\\zeta(s)$ 的非平凡零点实部都是 $\\frac{1}{2}$。它成立了 160 年，没有人证明，也没有人找到反例',
    '柯尼斯堡七桥问题是图论的起点：欧拉 1736 年证明不存在一次走完所有桥的路径，顺便发明了图论',
    'Cantor 证明实数比自然数"更多"——无穷也有大小之分。这个结果让他的导师 Kronecker 震怒，称他为"腐蚀年轻人的败类"',
    '哥德尔不完备定理说：任何足够强的公理系统都存在既无法证明也无法反驳的命题——包括"本系统是无矛盾的"这个命题本身',
    'Conway 的生命游戏只有四条规则，却能模拟自复制机器、图灵机，乃至任意计算过程',
    '三体问题没有解析解，但 Poincaré 在研究它的过程中发明了拓扑学和混沌理论——两个副产品比原问题更重要',
    'Hilbert 在 1900 年提出 23 个问题，其中 10 个至今悬而未决，包括黎曼猜想和 $P$ vs $NP$',
    'Jordan 曲线定理听起来直观，但早期严格证明并不简单。数学里"显然"往往正是最需要小心的地方',
    '数学中的"猜想"不一定是猜测——有些猜想有数百页的计算支撑，只差最后一步严格证明',
    '四色定理是第一个被计算机辅助证明的重大定理（1976 年），当时许多数学家质疑这算不算"真正的证明"',
    '巴拿赫-塔斯基悖论：可以把一个球分成有限个碎片，重新拼合成两个与原来等大的球。在现实世界当然不可能——因为用的是非可测集',
    'Wiles 证明费马大定理时，在最后阶段发现了一个严重漏洞，他独自在楼上工作了一年多才修补好，事后说那十四个月是"他一生中最美丽的孤独时光"',
    '质数定理说：不超过 $n$ 的素数个数约为 $n/\\ln n$。这个结果 1896 年被独立证明了两次，同一天',
    '阿贝尔与黎曼都是年轻夭折的天才——阿贝尔 26 岁，黎曼 39 岁——数学界不止一次感叹若他们多活二十年会改写多少历史',
    '庞加莱猜想说：每个单连通的紧致三维流形同胚于三维球面。它 1904 年被提出，2003 年由 Perelman 用黎曼流几何证明',
    '希尔伯特旅馆悖论：一家有无穷间客房的旅馆即使客满，也能在不驱逐任何旧客的情况下接待无穷多位新客——这就是可数无穷的本质',
    '$P$ vs $NP$ 是计算机科学最大的开放问题，千禧年大奖七题之一，奖金 100 万美元——但大多数数学家猜测 $P \\neq NP$，却无法证明',
    '最短描述原则（柯尔莫哥洛夫复杂度）给出了"随机"的严格定义：一个字符串的复杂度是能生成它的最短程序的长度',
    '所有大于 2 的偶数都能写成两个素数之和——这就是哥德巴赫猜想，提出于 1742 年，至今没有完整证明',
    '连续统假设说不存在"介于可数集与实数集之间"的无穷。哥德尔（1940）和科恩（1963）分别证明它与 ZFC 的独立性：既不能被证明，也不能被否定',
    '数学归纳法的"最强形式"是超穷归纳：对良序集上的每一个元素，证明如果在它之前的所有元素都满足性质，则它也满足——这覆盖了所有序数',
    '调和级数 $\\sum 1/n$ 发散，但发散得极慢——加前 $10^{43}$ 项也不超过 100',
    '欧拉常数 $\\gamma = \\lim_{n\\to\\infty}(\\sum_{k=1}^n 1/k - \\ln n) \\approx 0.5772$。没有人知道它是否是有理数',
    '鸽巢原理是数学中看起来最平凡、实际上最强大的工具之一：$n+1$ 只鸽子住 $n$ 个巢，必有一个巢住了至少两只',
    // ── 数学家野史 ──
    'Ramanujan 在没有正规数学教育的情况下，靠自学发现了数千个令职业数学家震惊的公式，包括对 $1/\\pi$ 的极快收敛级数',
    'Galois 在 20 岁之前就证明了五次方程没有根式解——那是 1830 年。两天后他在决斗中去世，留下一封彻夜写成的数学信',
    'Fermat 在书页空白处写道"我有一个绝妙的证明，但这里地方太小写不下"——350 年后 Wiles 才给出完整证明，用了 200 页',
    'Grothendieck 几乎凭一己之力重建了整个代数几何。1970 年他突然放弃数学，退居山林，此后再未发表论文',
    'Perelman 证明了庞加莱猜想，拒绝了菲尔兹奖和百万美元大奖，说"宇宙比钱更有趣"',
    'Emmy Noether 被纳粹驱逐出德国，流亡美国，她的对称-守恒定律被爱因斯坦称为"数学天才的最高成就"',
    'Ramanujan 说他的公式是梦中女神 Namagiri 显灵赐予的；Hardy 评价他是"每个世纪诞生不超过一次的天才"',
    'Euler 在双目失明后凭记忆口述，仍完成了约四分之一的全部科学产出——共 886 篇论文',
    'Gauss 17 岁时用圆规和直尺作出了正 17 边形，这在此前 2000 年无人能做到；他在日记里只写了一行字："17!"',
    'Abel 证明五次方程无根式解时只有 19 岁，随后他花钱自印论文寄给 Gauss，Gauss 将其束之高阁，Abel 26 岁死于贫困',
    '1954 年图灵被英国政府以"严重猥亵罪"判处化学阉割，一年后去世。2009 年首相为此正式道歉',
    'Sophie Germain 用男性笔名与 Gauss 通信多年；Gauss 得知真相后写道："一个真正懂数学的女人，这种罕见程度……"',
    '柯西一生发表了 800 余篇论文；有段时间法国科学院每周的论文集一半以上都是他写的，最后院方不得不限制每人每次提交的篇幅',
    '纳什因博弈论获得诺贝尔经济学奖时已在精神病院住了三十年；领奖时他说："人之所以理性，是因为他们选择了理性"',
    'Bourbaki 是一群法国数学家用的集体笔名，没有真实存在的"尼古拉·布尔巴基"；他们重写了整个现代数学的基础',
    'Cantor 晚年深受精神疾病困扰，多次住院；他在信中写道"我的理论不是我发明的，它们是上帝启示给我的"',
    '笛卡儿发明坐标系的灵感据说来自病床上，他看着天花板上的一只苍蝇——想到用两个数就能精确描述它的位置',
    '高斯的导师 Pfaff 一度认为高斯将是"我见过的有史以来最伟大的数学家"——事后他的预言被严重低估了',
    '泰勒斯是已知最早的希腊数学家，他在埃及期间用相似三角形计算出金字塔的高度，令法老惊叹不已',
    'Kolmogorov 8 岁时发现了等差数列前 n 项之和的公式，并将其投给了学校数学杂志；编辑回信说"我们已经知道这个了"',
    'Archimedes 被命令不得打扰时，对前来行刑的罗马士兵说："先等我做完这道题。"——然后被杀了',
    '莱布尼茨 1675 年在笔记本里第一次写下了 $\\int$ 这个符号；那一页纸现在保存在汉诺威图书馆',
    '华罗庚在抗战期间辗转流离，在破旧的茅屋里完成了解析数论的多项重要工作，后来那本《堆垒素数论》被翻译成多国语言',
    '陈景润证明了"1+2"（哥德巴赫猜想最接近完整证明的结论），据说他在狭小宿舍里不停演算，地板上铺满了草稿纸',
    '冯·诺依曼有着超乎常人的记忆力——据说他能背诵整本电话簿，并在谈话中突然引用多年前读过的一段话',
    '柯尼希定理在二分图中联系了最大匹配与最小顶点覆盖；它的发现者是匈牙利数学家 Kőnig Dénes，1916 年',
    'Weil 在二战期间因拒绝服兵役被关入监狱，却在狱中写出了代数几何的奠基性工作，后来说"监狱是我工作效率最高的地方"',
    '数学家 Paul Erdős 一生未定居，携带一只手提箱走遍全球，与 500 余位数学家合著论文，最多时一年参加 60 场研讨会',
    // ── 数学哲学与方法论 ──
    '"数学的本质不在于它的复杂性，而在于它如何将复杂转化为简单。" ——彭加莱',
    '数学证明有两种风格：构造性证明给出对象本身，非构造性证明只证明它存在却无法告诉你它在哪里',
    '一个命题"不平凡"意味着它的证明中有实质性创新——真正的工作在于找到那个关键思路',
    '数学没有权威，只有证明。即使是最权威的数学家发表的命题，只要证明有漏洞，它就是错的',
    '"好的数学像诗：一行抵千言，每个符号都不可缺少。" ——哈代',
    '现代数学建立在策梅洛-弗兰克尔公理（ZFC）之上；大多数人使用的数学，可以在 ZFC 里严格推导，尽管几乎没有人真的这样做',
    '反证法是一种优雅但有争议的技术：直觉主义者拒绝它，因为"不能不存在"不等于"存在"',
    '类比是数学中被低估的工具——很多领域的核心定理，第一步洞见来自与另一个领域结构的深刻类比',
    '数学证明不只是验证，它更是理解：一个好证明解释了"为什么"，一个平庸证明只告诉你"是"',
    '"如果你找不到短证明，通常意味着你还没有真正理解这个结论。" ——这是很多数学家共同的经验',
    '计算机辅助证明（如 Lean、Coq、Isabelle）正在改变数学验证的范式；2023 年 Lean 社区完成了 Fermat 大定理的一部分形式化',
    '在代数中，两个看起来完全不同的结构"同构"意味着它们本质上是同一个东西——换个角度看而已',
    '数学家用"显然"和"容易验证"时，往往是他们懒得写出来，而不是真的容易；读者应当对这两个词保持警惕',
    '泛化（generalization）是数学的核心引擎：把一个具体结论提升为抽象结构，往往会同时解锁数十个推论',
    '"数学的进步发生在研究边界上——那里两个不同的领域意外相遇。"——阿蒂亚爵士',
    // ── 更多有趣结论 ──
    '蒙提霍尔问题：三扇门后有一辆车，主持人打开了一扇有山羊的门，换门的获胜概率是 $\\frac{2}{3}$。这个反直觉结论曾引发数千封愤怒读者来信',
    '停机问题是图灵 1936 年证明的：不存在能判断任意程序是否会停机的算法——这是计算的根本极限',
    '生日悖论：23 个随机人中，至少两人同生日的概率超过 50%——几乎所有人第一次听到都不相信',
    'Collatz 猜想：任取正整数，若为偶数除以 2，若为奇数乘以 3 加 1，反复执行，最终总会到达 1。没有人能证明它，也没有人找到反例',
    '球面不能平铺到平面——这就是为什么世界地图总有变形；微分几何里的高斯绝妙定理给出了严格说明',
    'e 的无理性比 $\\pi$ 更容易证明；$\\pi$ 和 $e$ 的"代数独立性"（即它们之间不满足任何有理系数代数方程）至今未被证明',
    '素数间隙猜想：相邻素数之差可以任意大（例如 $n! + 2, \\ldots, n! + n$ 都是合数），但孪生素数猜想说差为 2 的素数对有无穷多个，也未被证明',
    '图同构问题的复杂度至今不明：它既没有被证明是 P 的，也没有被证明是 NP 完全的——是理论计算机科学中极罕见的"中间状态"',
    '最短路问题 Dijkstra 算法于 1956 年由 Dijkstra 在咖啡馆里用 20 分钟想出来，他说之所以优雅是因为"没有用纸笔推导，必须在脑子里保持简洁"',
    '数字 1729 是"Hardy-Ramanujan 数"——它是可以用两种不同方式表达为两个立方数之和的最小数：$1^3+12^3 = 9^3+10^3$',
    '所有凸多面体满足 $V - E + F = 2$（欧拉公式）。这是拓扑学的源头之一，也是多面体理论中被引用最多的单一结论',
    '非欧几何的诞生打破了"公理就是真理"的观念：高斯、鲍耶、罗巴切夫斯基分别独立发现，平行公设并非必然成立',
    '概率论的公理化直到 1933 年才由苏联数学家 Kolmogorov 完成；在此之前，"概率"只是一个直觉概念',
    '费波那契数列 $1, 1, 2, 3, 5, 8, \\ldots$ 出现在植物的叶序、螺旋贝壳、向日葵种子排列中；相邻项之比趋向黄金比例 $\\phi$',
    '图论中，Petersen 图是最小的 3-正则非哈密顿图，被许多图论猜想拿来当反例——它是图论界的"常见反例储备库"',
    '球的最密堆积猜想（Kepler 1611 年提出）直到 1998 年才由 Hales 用计算机辅助证明，整个证明有 300 页 + 大量代码',
    '测度论告诉我们：直线上的"几乎所有"实数是无理数——有理数虽然稠密，但其测度为零',
    '代数基本定理说：每个次数 $n \\geq 1$ 的复系数多项式恰好有 $n$ 个复根（含重数）。它的证明本质上是拓扑的，不是代数的',
    '复分析里的留数定理可以计算很多在实数范围内极难处理的积分，比如 $\\int_{-\\infty}^{\\infty} \\frac{\\sin x}{x} dx = \\pi$',
    '集合论中的良序定理与选择公理等价——Zermelo 1904 年证明了这一点，但它的证明是非构造性的，引发了激烈争议',
    '模运算让我们能用有限的计算处理无穷大的数，是密码学、计算机科学和数论的共同基础',
    '李群将代数与微分几何统一：光滑对称变换构成一个群，其"切空间"（李代数）携带了几乎所有局部信息',
    '范畴论（category theory）试图用"态射"和"函子"统一所有数学结构；有人称它为"数学的数学"，也有人戏称为"抽象废话"',
    '谱定理告诉我们：实对称矩阵总可以被正交化对角化——量子力学的可观测量都是厄米算符，其物理意义正来自这个定理',
    '"足够小的球"在平坦空间里是球；但在弯曲流形上，体积公式里多出了曲率修正项——这就是弯曲空间的感知方式',
    '整数分解目前没有已知的多项式时间算法；RSA 加密的安全性正是依赖于这一点',
    '二进制并非计算机的发明——莱布尼茨 1703 年就写了一篇论文，将二进制与中国《易经》的阴阳相对照',
    '指数增长常常超出直觉：将一张纸对折 42 次，厚度超过月球到地球的距离',
    '随机游走"几乎必然"在二维平面上无限次返回出发点，但在三维空间里不会——波利亚 1921 年证明了这一结果',
    '傅里叶级数最初被用来描述热传导（1822 年），后来成为信号处理、量子力学、图像压缩的统一语言',
    '零（0）作为独立数字的出现，是数学史上最革命性的发明之一——没有它，位值制记数法无从建立',
    '柏拉图体只有 5 种：正四面体、正六面体、正八面体、正十二面体、正二十面体——这是欧几里得《几何原本》最后一卷的核心结论',
    '证明两个图同构是 NP 的，但不知道是否在 P 内；图同构问题是理论计算机科学中少数几个复杂度未知的自然问题',
    '实数轴上的康托尔集测度为零，但"不可数"——它是分形的原始雏形，自相似性的经典演示',
    // --- 新增：数学野史与趣闻 ---
    '图灵在二战期间破解恩尼格玛密码机，背后依赖的是"模同余"与概率推理——纯数学工具拯救了数百万生命',
    '冯·诺依曼据说能以 20 倍速阅读书籍，并在脑中完整记忆。一次他当场口算出别人用计算机跑了 4 小时才得到的积分结果',
    'John Nash 在 21 岁写出一页半的博士论文，奠定博弈论"纳什均衡"基础，40 年后因此获得诺贝尔经济学奖',
    'G.H. Hardy 认为数学之美胜过一切，他把板球和数学列为人生两大乐趣，临终时说"没有任何遗憾，除了我没能证明黎曼猜想"',
    'Cauchy 一生发表 789 篇论文，以至于巴黎科学院不得不限制每位会员每月提交的论文数量——该规定在数学圈称为"Cauchy 规则"',
    '19 世纪末，Klein 和 Hilbert 为了谁才是哥廷根大学数学掌门人展开多年竞争；Hilbert 赢得了这场影响整个 20 世纪数学走向的争论',
    'Dirichlet 证明等差数列中有无穷多个素数时，引入了 L-函数，开创了解析数论——他曾说"任何人都能读懂我的证明，因为我避免了无用的推广"',
    '拓扑学家 Thurston 将几何化猜想（Poincaré 猜想的推广）作为他的研究纲领，他那篇论文改变了低维拓扑格局，但直到 Perelman 才完成证明',
    '张益唐 2013 年发表孪生素数界的突破性结果时，他已 58 岁，在大学里教了多年基础微积分；投稿前没有告诉任何人',
    'Langlands 纲领被称为"数学大统一理论"，连接数论、代数几何与表示论，至今仍是数学最前沿的研究方向之一',
    'Srinivasa Ramanujan 在 1918 年发现了 $\\tau$ 函数的乘性，这成为自守形式现代理论的起点——他靠直觉看到的结论，数学家花了几十年才证明',
    'Atiyah-Singer 指标定理统一了分析学与拓扑学，被称为"20 世纪最伟大的数学定理之一"，连接了算子的解析性质和流形的拓扑不变量',
    '罗素悖论（1901）让弗雷格的《算术基础》在付印前崩溃：弗雷格收到罗素的信后，在书的附录中写道"没有什么比发现自己的工作基础动摇更令人不快的了"',
    '费马数 $F_n = 2^{2^n}+1$：费马猜测它们全是素数，但 Euler 1732 年发现 $F_5$ 是合数；至今没有发现第 5 个之后的费马素数',
    '数学归纳法实际上比很多人想象的更微妙：它等价于自然数的良序性，而良序性本身等价于选择公理的一个弱形式',
    '海王星的发现完全靠数学：Adams 和 Leverrier 各自独立，仅凭天王星的轨道摄动，就用笔和纸算出了一颗未知行星的位置',
    '希尔伯特曾预言"没有无解的问题"，并以此激励哥廷根数学院；1931 年哥德尔不完备定理发表，直接回答了他的信念——有些问题在当前公理系统内永远无解',
    'Weyl 在量子力学的数学化中引入了群表示论，他说："理解物理，最终意味着找到它背后的群结构"',
    '英国数学家 Littlewood 与 Hardy 合作写了近 100 篇论文，却从未同时出现在同一个房间——他们通过信件协作，并约定可以完全无视对方的错误',
    '庞加莱猜想提出时（1904），人们以为这是个简单问题；它最终成为七大千禧年问题中唯一被解决的，而解决者 Perelman 拒绝了 100 万美元奖金',
    '莫比乌斯带（1858）不是 Möbius 首先发现的——Listing 独立地、更早地描述了同样的结构，数学命名并不总是最公平的',
    '代数拓扑中，基本群的概念由庞加莱引入；他注意到一个空间的"环路不能连续收缩"这一直觉，最终演变成了同伦论整个领域',
    '素数定理（$\\pi(n) \\sim n/\\ln n$）的两个独立证明者 Hadamard 和 de la Vallée-Poussin 分别活到了 97 岁和 95 岁，被数学圈调侃为"证明了素数定理可以长寿"',
    '数学中的"猜想"一旦被证明，通常立刻改名为"定理"——但有些习惯性叫法沿用至今，如费马大定理在被证明前 357 年都被称为"猜想"',
    'Gowers 用傅里叶分析证明了 Szemerédi 定理的定量版本，顺带发展出"高阶傅里叶分析"——他说这是他做过的最困难也最愉快的数学',
    '数学中的"错误证明"有时候反而更有价值：Lamé 和 Cauchy 各自宣布证明了费马大定理，但 Kummer 指出了致命错误，由此引入了"理想数"理论，成为代数数论的基石',
    '20 世纪数学最重要的会议之一：1900 年巴黎国际数学家大会，Hilbert 提出 23 个问题，引导了整整一个世纪的研究方向',
    // --- 新增：产品使用技巧 ---
    '"定理搜索"支持中英文混合查询——比如输入"紧集上连续函数有界 compact"可以同时匹配中英文来源',
    '在"学习模式"中，可以先输入一个宽泛的数学概念（如"测度论基础"），系统会自动拆解为若干子主题逐一展开',
    '"证明审查"模式支持上传 .tex 文件，如果你的 LaTeX 草稿还不能编译，可以直接粘贴 \\begin{proof}...\\end{proof} 片段',
    '每次对话都会保存在历史记录中，点击侧边栏可以随时回顾——包括完整的证明过程和 LaTeX 源码',
    '设置面板中可以随时切换 LLM 提供商；如果 Gemini 响应较慢，可切换到 DeepSeek，通常能加快响应速度',
    '"定理搜索"的结果卡片上有来源链接，点击可直达 arXiv 原文或 Stacks Project 对应页面，方便深度阅读',
    '问题求解后，每个回复气泡右下角都有 { } 按钮，可以将该条自然语言证明单独转换为 LaTeX，无需重新求解',
    '"证明审查"可以设置审查重点：在上传 PDF 时，在文本框中写明"重点检查第 3 节引理"，AI 会优先关注该部分',
    '如果 LaTeX 输出中的公式显示异常，可以将代码复制到 Overleaf 或本地 TeX 编辑器进行完整渲染和检查',
    '学习模式下，可以点击任一小节旁的"重新生成"按钮，只重新生成该节内容，不影响其他部分——适合针对性改进',
    '使用"定理搜索"时，描述越具体效果越好——"连续函数在紧集上一致连续"比"连续函数性质"精确得多',
    '系统支持 OpenAI 兼容的任意 API 中转站，在设置中填入 Base URL 即可，无需修改任何代码',
    // --- 新增：数学思想与名言 ---
    '"数学是上帝书写宇宙时使用的语言。" —— 伽利略',
    '"数学的本质在于它的自由。" —— 康托尔',
    '"没有什么比一个好的证明更令人满足的了，不是因为它的正确，而是因为它的美。" —— 哈代',
    '"数学家不是发明数学，而是发现它。" —— 哈代（柏拉图主义的经典表述）',
    '"对于大多数人来说，数学是一种工具；对于数学家来说，工具本身就是目的。" —— 冯·诺依曼',
    '"好的数学就像好的诗歌：最少的字，最深的意。" ——（数学圈流传的说法）',
    '"一个数学定理应该像一颗钻石：切割越精确，光芒越璀璨。" —— 波利亚',
    '"直觉是数学发现的源头，严格性是数学证明的保障，二者缺一不可。" —— 庞加莱',
    '"我们通过证明了解真理，但通过直觉发现真理。" —— 庞加莱',
    '"提出正确的问题，比回答问题更难。" —— 康托尔（也被其他数学家引用）',
    '"证明是使数学家信服的艺术。" —— 保罗·哈尔莫斯',
    '"真正的数学家不该害怕愚蠢的问题。" —— 保罗·埃尔德什',
    '"数学的进步依赖于两种力量：泛化的冲动和对具体例子的热爱。" —— 冯·诺依曼',
    // --- 新增：数学有趣知识 ---
    '质数 41 有一个神奇性质：$n^2 + n + 41$ 对 $n = 0, 1, \\ldots, 39$ 全都是质数——但 $n = 40$ 时结果是 $40^2 + 40 + 41 = 41^2$，不再是质数',
    '巴拿赫-塔斯基悖论在 $\\mathbb{R}^2$ 中不成立，因为平面圆盘不能被分解成有限个片段再拼成两个相同的圆盘——悖论依赖于三维旋转群的特殊性质',
    '四色定理（1976）是计算机辅助证明的先驱，程序需要检查 1936 个约化构型；直到 2005 年才有人给出了更简洁的（但仍需计算机的）形式化验证',
    '整数分拆中，将 $n$ 分拆为奇数之和的方案数等于分拆为互不相同整数之和的方案数——这是欧拉发现的一个优雅双射',
    '代数中的"幺半群"这个名字来自法语 monoïde，由数学家 Bourbaki 组的成员创造——Bourbaki 学派因发明了大量数学术语而闻名（也被调侃）',
    '调和级数 $1 + 1/2 + 1/3 + \\ldots$ 发散极其缓慢，前一百万项之和约为 14.4，前 $10^{43}$ 项之和才超过 100',
    '傅里叶变换最初是为了解热传导方程，但现在它存在于 MRI 成像、MP3 压缩、地震分析、股票预测——几乎所有需要分解频率的领域',
    '数学中有一类"超越数"，它们不是任何有理系数多项式的根。虽然几乎所有实数都是超越数，但证明一个具体的数是超越的通常极其困难',
    '1+2+3+... 的"和"被正则化为 $-1/12$ 不是通常意义的求和，而是 Ramanujan 求和或黎曼 $\\zeta$ 函数在 $s=-1$ 处的解析延拓值',
    '线性代数中，矩阵乘法不满足交换律，但行列式满足：$\\det(AB) = \\det(A)\\det(B)$——这个等式在高维空间里意味着"体积的缩放可以分步计算"',
    '连续统假设（CH）说 $\\aleph_0$（可数无穷）和 $2^{\\aleph_0}$（实数基数）之间没有中间基数；哥德尔（1940）和科恩（1963）分别证明 CH 在 ZFC 中既不能被证明也不能被否定',
    'Ramsey 理论说：足够大的结构中必然存在有序子结构。最著名的例子是 $R(3,3)=6$：6 人中必有 3 人互相认识或互相不认识',
    '拓扑学中，咖啡杯和甜甜圈"同胚"——可以连续变形为对方而不撕裂或粘合。这是因为两者都只有一个"洞"（亏格为 1）',
    '复数的引入并非为了美观，而是为了求三次方程的实数根——16 世纪意大利数学家卡尔达诺发现，即使最终答案是实数，中间步骤也必须经过复数',
    '哥德巴赫猜想至今未证：每个大于 2 的偶数都能写成两个素数之和。已通过计算机验证到 $4 \\times 10^{18}$，却仍无一般性证明',
    '"非欧几何"的发现让数学家意识到公理系统可以有多个不同的"实现"——这一认识后来发展成了现代数学的公理化方法和模型论',
    '密码学中的椭圆曲线（ECC）利用了椭圆曲线群上的离散对数难题；Bitcoin 的签名算法 secp256k1 就是一条精心选择的椭圆曲线',
    '数学中有些定理的证明长达数百页甚至数千页，比如有限单群分类定理总长超过 10000 页，由数十位数学家历经数十年完成',
    '蒙提霍尔问题（三门问题）之所以出名，是因为连美国顶尖数学家收到玛丽莲的解答后也写信反对——直到计算机模拟彻底说服了他们',
    // --- 补充至 225+ ---
    '数学中的"对偶"思想无处不在：线性代数里向量与对偶空间，拓扑里开集与闭集，逻辑里 AND 与 OR——找到对偶往往意味着获得"免费"的另一个定理',
    '微积分基本定理揭示了微分与积分互为逆运算，这一发现使得牛顿和莱布尼茨几乎同时建立了微积分，也引发了史上最著名的优先权之争',
    'Cauchy 不等式 $|\\langle u, v \\rangle|^2 \\leq \\langle u,u \\rangle \\langle v,v \\rangle$ 在内积空间中成立，它是物理中不确定性原理的数学根源',
    '格罗滕迪克在其自传《收获与播种》中描述了 12 个他认为改变了数学的思想，其中"拓扑斯"和"动机"理论至今仍是研究前沿',
    '泰勒展开将无穷可微函数表示为幂级数——这一工具不仅是分析的核心，也是物理学中"小角近似"等工程方法的严格基础',
    '数学里的"同构"和"等价"是截然不同的概念：同构保留所有结构，等价只保留某些性质——区分清楚这两者，可以避免很多混乱',
    'Stirling 公式 $n! \\approx \\sqrt{2\\pi n}(n/e)^n$ 让人们在计算大阶乘时无需逐步相乘，广泛用于概率论、统计物理和算法复杂度分析',
    '1637 年笛卡尔引入坐标系，将几何问题翻译成代数方程——这是数学史上最具影响力的"语言转换"之一，直接推动了解析几何的诞生',
    '波利亚的《怎样解题》（1945）归纳了解题的四步法：理解问题、制定计划、执行计划、回顾反思——至今仍是数学教育的经典参考书',
    '整个实分析建立在"完备性"之上：实数的完备性意味着柯西列必收敛，这一性质使得极限、微积分的严格化成为可能',
    'RSA 加密的安全性依赖大整数分解的困难——而 Shor 算法（1994）表明量子计算机可以高效分解大整数，一旦实用化将使 RSA 失效',
    '凸优化在机器学习中无处不在：支持向量机（SVM）的训练本质上是一个凸二次规划问题，这保证了全局最优解的存在性和唯一性',
    '数列 $1, 1/2, 1/4, 1/8, \\ldots$ 的无穷和为 $2$——这让古代哲学家困惑了几个世纪（芝诺悖论），而严格的极限理论在 19 世纪才给出了令人信服的解答',
    '无穷大的"大小"有层次：$\\aleph_0 < 2^{\\aleph_0} < 2^{2^{\\aleph_0}} < \\ldots$，这个无穷层次结构由康托尔发现，打破了"无穷只有一种"的直觉',
    '数学中的美学标准之一是"证明的长度"——一个一行的证明往往比一个三十页的证明更受推崇，即使两者都正确',
    '拉格朗日乘数法允许我们在约束条件下求极值，它将有约束优化问题转化为求一个扩展函数的无约束极值，是工程与经济学中的核心工具',
    '"结构上的相似"是数学发展的驱动力——环、域、群的定义抽象了数字运算的本质，使得同一套理论可以同时适用于整数、多项式和旋转变换',
    '数学证明中"构造性"与"非构造性"的区别：构造性证明给出一个具体的对象，非构造性证明（如反证法）只证明存在性却不给出构造——两派数学家至今仍有争论',
    '实变函数中 Lebesgue 积分取代 Riemann 积分的关键优势：它能处理 Riemann 积分无法定义的函数（如处处不连续的 Dirichlet 函数），并满足更好的极限定理',
    '庞加莱回归定理：在某些动力系统中，几乎所有轨道都会无限次地回到起点附近——这意味着一个封闭的物理系统在足够长时间后会"几乎"回到初始状态',
    '"问题求解"模式可以处理多步骤证明；如果某一步你已知，可以在输入中明确说明"假设引理 X 成立"，AI 会以此为基础继续推导',
    '我爱数学，这就是我为什么开发 vibe proving。',
  ],
  en: [
    // ── Feature introductions ──
    '"Problem Solving" mode is designed for research-level mathematical questions',
    'Theorem Search queries 9M+ theorems and returns real paper sources, authors, and links',
    'Paste any proof into "Proof Review"; the AI verifies each logical step independently, without seeing the author\'s reasoning',
    'Upload math papers to your Project and the AI will prioritize your knowledge base when answering',
    '"Proof Review" supports uploading .tex / .md files, so you can review a LaTeX paper draft directly',
    'In "Formalization" mode, the system first searches mathlib4 for an existing theorem, then tries to generate Lean 4 code and verify it with local compilation',
    'After uploading a textbook, Learning Mode will prioritize your uploaded material when explaining theorems',
    'Log "Open Questions" in your Project to resume complex investigations across multiple sessions',
    'Paste a proof you\'re unsure about into "Proof Review" — the AI will pinpoint exactly which steps are unjustified',
    // ── Usage tips ──
    'After a proof streams in, hover over the AI bubble — a { } LaTeX button appears in the action bar. Click it to generate compilable LaTeX source code',
    'In Learning Mode, click "Regenerate" next to any section header to regenerate just that section — no need to re-run the full flow',
    'If a theorem name appears in a proof but you are unsure of its content, paste the name into "Theorem Search" — it usually returns the source immediately',
    'For PDF knowledge-base uploads, files under 5 MB work best; larger PDFs can be split by chapter using pdfcrop or ghostscript before uploading',
    'DeepSeek in the model dropdown is cost-efficient for iterative verification; Gemini excels at exploratory reasoning for complex conjectures',
    'The LaTeX panel appears on the right side of a solve result — copy and paste directly into Overleaf for a fully compilable document',
    'Past sessions are saved locally in the browser; multiple attempts at the same problem are stored as separate sessions for easy comparison of proof paths',
    'Formalization first queries mathlib4 — if a matching theorem exists it returns Lean 4 code immediately; generation only starts if no match is found',
    'If the solver "actively refuses" (very low confidence), it usually means a hypothesis is missing or the statement is a known open problem — check "Theorem Search" to confirm',
    'For difficult problems, splitting the task into 2 or 3 lemmas usually works better than asking for a complete proof in one shot',
    'Try different models from the dropdown on the same statement — their proof styles can vary dramatically',
    'If a statement keeps resisting proof, check "Theorem Search" for its standard name, classical equivalent forms, or known special cases — that often reveals the right entry point',
    'If you are writing a paper, you can first ask the AI for a proof blueprint, then rewrite the key steps in your own notation and expository style',
    'Many statements that look true are missing exactly one condition; when the system finds a counterexample, the real value is seeing which hidden assumption failed',
    'The progress bar reaching 100% means the server finished processing; complex PDFs can take several minutes — the trivia tips keep you company',
    'Track each concept\'s learning state in Project Management (Unseen → Confused → Understood → Mastered) to build your own knowledge graph',
    'The "Prerequisites" section in Learning Mode gives you a quick checklist of what you need to know before the current proof — ideal for identifying gaps',
    'A step flagged as a "gap" in Proof Review is usually where the logical leap is largest — that\'s where a new lemma is most needed',
    'For analysis or measure-theory statements, try asking for the intuition first, then request a rigorous $\\epsilon$-$\\delta$ proof as a second step',
    'In Theorem Search, describe concretely: add field names, boundary conditions, or equivalent formulations — it dramatically improves accuracy',
    // ── Classical results and math trivia ──
    'Euler\'s identity $e^{i\\pi}+1=0$ unites the five most fundamental numbers in mathematics — voted the "most beautiful formula" by generations of mathematicians',
    'Euclid\'s proof of infinitely many primes fits in five lines and is unchanged after 2300 years',
    'The irrationality of $\\sqrt{2}$ was discovered by ancient Greeks — and legend says the first person to prove it was drowned for revealing the secret',
    'The Riemann Hypothesis says all non-trivial zeros of $\\zeta(s)$ have real part $\\frac{1}{2}$. It has stood for 160 years with no proof and no counterexample',
    'The Königsberg bridge problem launched graph theory: Euler proved in 1736 that no single path crosses each bridge exactly once — and invented a new field in the process',
    'Cantor proved that some infinities are larger than others. His mentor Kronecker called him "a corrupter of youth." History sided with Cantor',
    'Gödel\'s incompleteness theorem: any sufficiently powerful system contains true statements it cannot prove — including the statement "this system is consistent"',
    'Conway\'s Game of Life has four rules and can simulate self-replicating machines, Turing machines, and arbitrary computation',
    'The three-body problem has no closed-form solution, but Poincaré invented topology and chaos theory while failing to solve it — better side effects than the original goal',
    'Hilbert\'s 23 Problems from 1900: 10 remain unsolved, including the Riemann Hypothesis and $P$ vs $NP$',
    'The Jordan curve theorem sounds intuitive, but early fully rigorous proofs were far from trivial. In mathematics, "obvious" is often where extra care is needed',
    'A "conjecture" in mathematics isn\'t just a guess — some have hundreds of pages of supporting computation, waiting only for the final rigorous proof',
    'The four-color theorem was the first major result proved with computer assistance (1976). Many mathematicians debated whether that could count as a "real proof"',
    'The Banach-Tarski paradox: a single ball can be decomposed into finitely many pieces and reassembled into two balls identical to the original — impossible in practice because it uses non-measurable sets',
    'Wiles found a serious gap in his proof of Fermat\'s Last Theorem at the last stage and spent over a year alone repairing it. He later called those fourteen months "the most beautiful solitude of my life"',
    'The prime number theorem — approximately $n/\\ln n$ primes up to $n$ — was proved independently by two people on the same day in 1896',
    'Both Abel and Riemann died young — Abel at 26, Riemann at 39. Mathematicians have long wondered what further landscapes they would have opened had they lived another twenty years',
    'The Poincaré conjecture — every simply-connected compact 3-manifold is homeomorphic to the 3-sphere — was stated in 1904 and proved by Perelman in 2003 using Ricci flow with surgery',
    'Hilbert\'s Hotel: an infinite hotel, fully occupied, can still accommodate infinitely many new guests — that is the essence of countable infinity',
    '$P$ vs $NP$ is one of the Millennium Prize Problems with a $1 million reward. Most mathematicians believe $P \\neq NP$, but no one can prove it',
    'Kolmogorov complexity gives a rigorous definition of randomness: the complexity of a string is the length of the shortest program that produces it',
    'Every even integer greater than 2 is conjectured to be the sum of two primes — Goldbach\'s conjecture, proposed in 1742, still unproven',
    'The Continuum Hypothesis — no set has cardinality strictly between the naturals and the reals — is independent of ZFC: both it and its negation are consistent with the axioms',
    'The harmonic series $\\sum 1/n$ diverges, but so slowly that summing the first $10^{43}$ terms still does not exceed 100',
    'The Euler–Mascheroni constant $\\gamma \\approx 0.5772$ is the limit of $\\sum_{k=1}^n 1/k - \\ln n$. Nobody knows if it is rational or irrational',
    'The pigeonhole principle — $n+1$ pigeons in $n$ holes means at least one hole has two — is one of the most elementary yet powerful tools in combinatorics',
    // ── Mathematicians' stories ──
    'Ramanujan discovered thousands of formulas — including a remarkably fast series for $1/\\pi$ — with no formal training, teaching himself from a single borrowed textbook',
    'Galois proved the quintic has no radical solution before age 20. He spent his last night writing mathematics before dying in a duel at 21',
    'Fermat wrote: "I have a truly marvelous proof, but this margin is too small to contain it." It took 350 years and 200 pages to settle',
    'Grothendieck almost single-handedly rebuilt the foundations of algebraic geometry. In 1970 he abruptly abandoned mathematics and retreated to a mountain village, publishing nothing thereafter',
    'Perelman proved the Poincaré conjecture, then declined both the Fields Medal and $1 million prize, saying "the universe is more interesting than money"',
    'Emmy Noether was expelled from Germany by the Nazis; Einstein called her theorem linking symmetry and conservation laws "the most significant creative mathematical genius thus far produced"',
    'Ramanujan claimed his formulas were revealed to him in dreams by a goddess. Hardy called him "a mathematician of the highest quality, a man in whose work there is a unique element of the truly marvelous"',
    'Euler lost sight in both eyes yet dictated roughly a quarter of his entire output — 886 papers — from memory alone',
    'At 17, Gauss constructed a regular 17-gon with compass and straightedge — a feat no one had achieved in 2000 years. His diary entry read simply: "17!"',
    'Abel proved the quintic unsolvable at 19, self-printed his paper and sent it to Gauss — who never opened it. Abel died in poverty at 26',
    'Alan Turing was prosecuted for "gross indecency" in 1952 and subjected to chemical castration. The British Prime Minister issued a formal apology in 2009',
    'Sophie Germain corresponded with Gauss under a male pseudonym for years. When Gauss learned the truth, he wrote that her "rare courage" had earned her "the most eminent rank"',
    'Cauchy published over 800 papers; at one point he submitted so many that the French Academy had to cap individual submissions per issue to make room for others',
    'Nash won the Nobel Prize in Economics after thirty years in a psychiatric institution. At the ceremony he said: "To be rational is a choice"',
    'Bourbaki is the collective pseudonym of a group of French mathematicians. There is no real Nicolas Bourbaki — they rewrote the foundations of modern mathematics under a fictional identity',
    'Cantor suffered repeated mental breakdowns in his later years. He wrote in letters: "My theory was not invented by me — it was revealed to me by God"',
    'Descartes\' idea of coordinates is said to have come to him while lying ill, watching a fly on the ceiling: he realized two numbers could pinpoint its exact location',
    'Kolmogorov solved three classic problems by age 19 and submitted one paper to a journal as a schoolboy. The editor replied: "We already know this." He later founded modern probability theory',
    'Archimedes, told not to disturb his circles, said to the Roman soldier sent to execute him: "Please wait until I finish this proof." He was killed immediately after',
    'Leibniz wrote the symbol $\\int$ for the first time in a notebook on 29 October 1675. That page is preserved in the Hanover library',
    'Von Neumann\'s memory was legendary — he could reportedly recite entire phone books and spontaneously quote a passage read years earlier in the middle of conversation',
    'Paul Erdős never had a permanent home, traveled the world with a single suitcase, and co-authored papers with over 500 mathematicians — at his peak, 60 conferences in a single year',
    'André Weil wrote some of his most foundational algebraic-geometry papers while imprisoned for refusing military service in WWII. He later said prison had been his most productive working environment',
    'The number 1729 — the Hardy–Ramanujan number — is the smallest expressible as the sum of two positive cubes in two different ways: $1^3 + 12^3 = 9^3 + 10^3$',
    // ── Philosophy and methodology ──
    '"The essence of mathematics lies in its freedom." — Cantor',
    'There are two flavors of proof: a constructive proof exhibits the object, a non-constructive proof only guarantees existence without showing how to find it',
    'Mathematics has no authority — only proofs. Even the most celebrated mathematician\'s theorem is wrong if the proof has a gap',
    '"Good mathematics is like poetry: one line outweighs a thousand words, and every symbol is indispensable." — Hardy',
    'Proof by contradiction is elegant but contested: constructivists reject it, since "cannot not exist" does not equal "exists"',
    'Analogy is one of mathematics\' most underrated tools — many of the core theorems in a field were first glimpsed through a deep structural parallel with another field',
    'A proof is not merely verification; it is understanding. A good proof explains the *why*, not just the *that*',
    '"If you can\'t find a short proof, you probably haven\'t understood the result yet." — a maxim shared by many working mathematicians',
    'Computer-assisted proofs (Lean, Coq, Isabelle) are reshaping mathematical verification; in 2023 the Lean community completed a formal verification of parts of the proof of Fermat\'s Last Theorem',
    'Two algebraic structures that are "isomorphic" are essentially the same object — just viewed from a different angle',
    'When mathematicians write "obvious" or "clearly", it usually means they are too tired to write it out — readers should treat these words as red flags',
    'Generalization is the central engine of mathematics: lifting a concrete result to an abstract structure often unlocks dozens of corollaries at once',
    '"Progress in mathematics happens at the boundary — where two different fields unexpectedly meet." — Sir Michael Atiyah',
    // ── More beautiful results ──
    'The Monty Hall problem: three doors, one car; the host opens a goat door; switching wins with probability $\\frac{2}{3}$. This counterintuitive result provoked thousands of angry letters when first published',
    'The halting problem — proved by Turing in 1936 — shows no algorithm can decide whether an arbitrary program halts. This is a fundamental limit of computation itself',
    'The birthday paradox: among just 23 randomly chosen people, the probability that two share a birthday exceeds 50% — almost nobody believes this at first',
    'The Collatz conjecture: take any positive integer; if even, halve it; if odd, multiply by 3 and add 1; repeat. It always reaches 1 — or so it seems. No proof exists, and no counterexample has been found',
    'A sphere cannot be flattened onto a plane without distortion — this is why every world map is inaccurate. Gauss\'s Theorema Egregium makes this rigorous',
    'The irrationality of $e$ is easy to prove; the "algebraic independence" of $\\pi$ and $e$ (no algebraic relation with rational coefficients between them) remains unproved',
    'The twin prime conjecture — infinitely many pairs of primes differing by 2 — remains open, though in 2013 Zhang Yitang proved there exist infinitely many prime pairs with gap less than 70 million',
    'Graph isomorphism is in NP but not known to be either in P or NP-complete — one of the very few natural problems whose complexity class is genuinely unknown',
    'Dijkstra invented his shortest-path algorithm in a coffee shop in 20 minutes, deliberately working without pen and paper to keep it clean. He published it in 1959 in a three-page paper',
    'Every convex polyhedron satisfies $V - E + F = 2$ (Euler\'s formula) — one of the most-cited single results in topology and the seed of an entire field',
    'Non-Euclidean geometry shattered the idea that axioms are self-evident truths: Gauss, Bolyai, and Lobachevsky independently discovered that the parallel postulate need not hold',
    'Probability theory was not axiomatized until 1933, when Kolmogorov placed it on a rigorous measure-theoretic foundation. Before that, "probability" was purely intuitive',
    'The Fibonacci sequence $1, 1, 2, 3, 5, 8, \\ldots$ appears in phyllotaxis, spiral shells, and sunflower seed arrangements; ratios of consecutive terms converge to the golden ratio $\\phi$',
    'The sphere-packing conjecture (Kepler 1611) was settled in 1998 by Hales using computer assistance — the proof runs to 300 pages plus extensive code',
    'Measure theory reveals that "almost all" real numbers on the number line are irrational — the rationals, though dense, have measure zero',
    'The fundamental theorem of algebra says every degree-$n$ polynomial over $\\mathbb{C}$ has exactly $n$ roots (with multiplicity). Its proof is essentially topological, not algebraic',
    'The residue theorem in complex analysis lets us evaluate many real integrals that are intractable otherwise — for instance, $\\int_{-\\infty}^{\\infty} \\frac{\\sin x}{x}\\,dx = \\pi$',
    'The well-ordering theorem is equivalent to the axiom of choice — proved by Zermelo in 1904 via a non-constructive argument that sparked fierce controversy',
    'Modular arithmetic lets finite computation handle arbitrarily large numbers; it underlies cryptography, computer science, and number theory simultaneously',
    'Lie groups unify algebra and differential geometry: smooth symmetry transformations form a group whose "tangent space" (the Lie algebra) encodes almost all local structure',
    'Category theory tries to unify all mathematical structures via "morphisms" and "functors". Some call it "the mathematics of mathematics"; others jokingly call it "abstract nonsense"',
    'The spectral theorem says every real symmetric matrix can be orthogonally diagonalized — quantum mechanics inherits this directly: all observables are Hermitian operators',
    'Integer factorization has no known polynomial-time algorithm — the security of RSA encryption rests entirely on this computational gap',
    'Binary representation was not invented by computers — Leibniz wrote a paper in 1703 connecting binary notation to the yin-yang duality of the I Ching',
    'Exponential growth defeats intuition: fold a sheet of paper 42 times and the stack would reach from Earth to the Moon',
    'A 2D random walk returns to its starting point with probability 1 (Pólya 1921), but a 3D random walk escapes to infinity with positive probability — dimension changes everything',
    'Fourier series were invented to solve heat equations (1822) and became the shared language of signal processing, quantum mechanics, and image compression',
    'Zero as an independent numeral is one of the most revolutionary inventions in mathematical history — without it, positional notation is impossible',
    'The five Platonic solids are the only regular convex polyhedra in three dimensions: tetrahedron, cube, octahedron, dodecahedron, icosahedron — the climax of Euclid\'s Elements',
    'The Cantor set has measure zero but is uncountable — the original fractal, a perfect demonstration of self-similarity long before "fractal" was a word',
    'The Collatz conjecture has been verified computationally for all integers up to $2^{68}$, yet remains completely unproved — a humbling reminder that patterns can mislead',
    'Knot theory, which classifies mathematical knots up to isotopy, unexpectedly became a powerful tool in molecular biology — DNA supercoiling is essentially a knot theory problem',
    // --- New: Math history & anecdotes ---
    'Alan Turing\'s codebreaking at Bletchley Park relied on modular arithmetic and probabilistic reasoning — pure mathematics saved millions of lives in WWII',
    'John von Neumann could read books at 20× speed and recall them verbatim. He once mentally solved in minutes an integral that had taken a computer four hours to evaluate',
    'John Nash\'s doctoral thesis — just one and a half pages — established the Nash equilibrium concept at age 21; forty years later it earned him the Nobel Prize in Economics',
    'G.H. Hardy listed cricket and mathematics as his two great loves; on his deathbed he said he had no regrets, except for never having proved the Riemann hypothesis',
    'Cauchy published 789 papers in his lifetime, forcing the Paris Academy to impose a monthly submission limit — a rule still called the "Cauchy rule" in mathematical circles',
    'Dirichlet introduced L-functions to prove infinitely many primes in arithmetic progressions, pioneering analytic number theory. He once said: "anyone can follow my proofs because I avoid useless generality"',
    'Thurston\'s geometrization programme — a vast extension of Poincaré\'s conjecture — reshaped low-dimensional topology; Perelman completed the proof four decades later',
    'Yitang Zhang published his breakthrough on bounded prime gaps in 2013 at age 58, after years teaching freshman calculus. He told no one before submitting',
    'The Langlands programme, connecting number theory, algebraic geometry and representation theory, is sometimes called "the grand unified theory of mathematics"',
    'Ramanujan\'s discovery of the multiplicativity of the tau function in 1918 seeded the modern theory of automorphic forms — his intuition outpaced formal proof by decades',
    'The Atiyah–Singer index theorem unifies analysis and topology by linking the analytic index of an elliptic operator to the topological invariants of the underlying manifold',
    'Russell\'s paradox (1901) shattered Frege\'s Foundations of Arithmetic before it was even printed; Frege wrote in an appendix: "Nothing is more unwelcome than to find the foundations shaking"',
    'Fermat numbers $F_n = 2^{2^n}+1$: Fermat conjectured they were all prime, but Euler found $F_5$ is composite in 1732; no prime Fermat number beyond $F_4$ has been found since',
    'Mathematical induction is subtler than it looks: it is equivalent to the well-ordering of the natural numbers, which is in turn equivalent to a weak form of the axiom of choice',
    'Neptune was discovered entirely by mathematics: Adams and Leverrier independently predicted its position from perturbations in Uranus\'s orbit, using only pen, paper, and Newton\'s laws',
    'Hilbert declared "there are no unsolvable problems" — Gödel\'s incompleteness theorems (1931) answered him directly: some problems can never be resolved within a given axiomatic system',
    'Weyl introduced group representation theory into quantum mechanics and said: "to understand physics ultimately means to find the group structure behind it"',
    'Hardy and Littlewood wrote nearly 100 joint papers yet rarely appeared in the same room — they collaborated entirely by letter, with a rule allowing each to completely ignore the other\'s mistakes',
    'The Poincaré conjecture was considered easy at first; it became the only one of the seven Millennium Problems to be solved — and the solver, Perelman, declined the $1 million prize',
    'The Möbius strip was independently discovered by Listing (earlier) and Möbius; Möbius got the name. Mathematical naming is not always fair',
    'The two independent provers of the Prime Number Theorem — Hadamard and de la Vallée-Poussin — lived to 97 and 95 respectively; the math community jokes that proving it confers longevity',
    'Gowers used higher-order Fourier analysis to prove a quantitative version of Szemerédi\'s theorem; he described it as the hardest and most enjoyable mathematics he had ever done',
    '"Wrong proofs" can be more valuable than correct ones: Lamé and Cauchy both claimed to prove Fermat\'s Last Theorem, but Kummer\'s refutation led him to invent ideal numbers — the foundation of algebraic number theory',
    // --- New: Product tips ---
    'TheoremSearch supports mixed-language queries — typing "compact continuous bounded 紧集连续" can match results from both English and Chinese-indexed sources',
    'In Learning mode, start with a broad concept like "measure theory basics"; the system will break it into sub-topics and expand each one systematically',
    'Proof Review accepts .tex files; if your LaTeX draft doesn\'t compile yet, you can paste a raw \\begin{proof}...\\end{proof} block directly',
    'Every conversation is saved to the history sidebar — including full proof steps and generated LaTeX source code — so you can revisit or compare sessions anytime',
    'You can switch LLM providers in the settings panel at any time. If Gemini is slow, switching to DeepSeek usually gives faster responses',
    'Theorem search result cards contain source links — click to jump directly to the original arXiv paper or Stacks Project page',
    'After each solve, the { } button on each message bubble lets you independently convert that specific natural-language proof to LaTeX — no need to re-run the solve',
    'In Proof Review, you can specify a focus: type "focus on Lemma 3.2" in the text box when uploading, and the AI will prioritise that section',
    'If a generated LaTeX formula renders oddly, copy the source code to Overleaf or a local TeX editor for a complete render and diagnosis',
    'In Learning mode, the "Regenerate" button next to any section regenerates only that section — perfect for iterative improvement without rerunning everything',
    'The more specific your TheoremSearch query, the better: "uniformly continuous on compact set" finds far more relevant results than "continuity properties"',
    'The system supports any OpenAI-compatible API relay — just fill in the Base URL in settings; no code changes needed',
    // --- New: Mathematical ideas & quotes ---
    '"Mathematics is the language in which God has written the universe." — Galileo',
    '"The essence of mathematics lies in its freedom." — Cantor',
    '"Nothing satisfies quite like a good proof — not because it is correct, but because it is beautiful." — Hardy',
    '"A mathematician does not invent mathematics; he discovers it." — Hardy (the Platonist position)',
    '"For most people mathematics is a tool; for mathematicians, the tool is the goal." — von Neumann',
    '"Good mathematics is like good poetry: maximum meaning, minimum words." — mathematical folklore',
    '"A theorem should be like a diamond: the more precisely it is cut, the more brilliantly it shines." — Pólya',
    '"Intuition is the source of mathematical discovery; rigour is the guarantee of mathematical proof." — Poincaré',
    '"We know truth through proof, but discover it through intuition." — Poincaré',
    '"Asking the right question is harder than answering it." — often attributed to Cantor and others',
    '"A proof is a device for convincing mathematicians." — Paul Halmos',
    '"A real mathematician is not afraid of a stupid question." — Paul Erdős',
    // --- New: Mathematical facts & curiosities ---
    'The prime $41$ generates a remarkable sequence: $n^2+n+41$ is prime for $n=0,1,\\ldots,39$, but composite at $n=40$ where it equals $41^2$',
    'The Banach–Tarski paradox fails in $\\mathbb{R}^2$: a disc cannot be decomposed into finitely many pieces and reassembled into two copies — the paradox relies on special properties of 3-D rotations',
    'The four-colour theorem (1976) pioneered computer-assisted proof, requiring the checking of 1936 reducible configurations; a more streamlined computer verification appeared in 2005',
    'Euler discovered that the number of partitions of $n$ into odd parts equals the number of partitions into distinct parts — an elegant bijection hidden in a generating-function identity',
    'The harmonic series $1+1/2+1/3+\\cdots$ diverges glacially slowly: the first million terms sum to about 14.4, and it takes more than $10^{43}$ terms to exceed 100',
    'The Fourier transform was invented to solve the heat equation, but now underpins MRI imaging, MP3 compression, seismic analysis, and financial time-series modelling',
    'Almost all real numbers are transcendental, yet proving that any specific number is transcendental is typically extremely difficult',
    'The "sum" $1+2+3+\\cdots = -1/12$ is not ordinary summation; it is the analytic continuation of the Riemann $\\zeta$ function evaluated at $s=-1$',
    'Matrix multiplication is not commutative, but determinants are: $\\det(AB)=\\det(A)\\det(B)$ — meaning "volume scaling factors multiply" regardless of the order of operations',
    'The Continuum Hypothesis — that there is no cardinal between $\\aleph_0$ and $2^{\\aleph_0}$ — was proved independent of ZFC: Gödel (1940) showed it cannot be disproved; Cohen (1963) showed it cannot be proved',
    'Ramsey theory guarantees that sufficiently large structures must contain ordered sub-structures. The classic result: among any six people, three must be mutually acquainted or mutually strangers ($R(3,3)=6$)',
    'In topology, a coffee cup and a doughnut are homeomorphic — continuously deformable into each other without tearing or gluing, since both have exactly one hole (genus 1)',
    'Complex numbers were not invented for elegance but to solve real cubic equations: 16th-century Italian algebraists found that extracting a real root can require intermediate complex arithmetic',
    'Goldbach\'s conjecture has been computationally verified up to $4\\times 10^{18}$ but remains unproved: every even integer greater than 2 is the sum of two primes',
    'The discovery of non-Euclidean geometry revealed that axiomatic systems can have multiple distinct models — a realisation that eventually led to modern model theory and formal logic',
    'Elliptic curve cryptography (ECC) exploits the difficulty of the discrete logarithm problem on an elliptic curve group; Bitcoin\'s signature algorithm uses the carefully chosen curve secp256k1',
    'The classification of finite simple groups spans over 10,000 pages of journal articles, written by dozens of mathematicians over several decades — the longest proof in history',
    'The Monty Hall problem became famous partly because top mathematicians wrote angry letters insisting the published solution was wrong — until computer simulations settled the debate',
    'A space-filling curve (Peano 1890) maps the unit interval continuously onto the unit square — a result so counterintuitive that it forced mathematicians to rethink "dimension"',
    'Knot theory, which classifies mathematical knots up to isotopy, unexpectedly became a powerful tool in molecular biology — DNA supercoiling is essentially a knot theory problem',
    // --- Extra entries to reach 225+ ---
    'The idea of "duality" pervades mathematics: vectors and dual spaces in linear algebra, open/closed sets in topology, AND/OR in logic — finding a dual often gives you a second theorem for free',
    'The Fundamental Theorem of Calculus reveals that differentiation and integration are inverse operations — the discovery that caused Newton and Leibniz to dispute priority in one of history\'s most famous intellectual feuds',
    'The Cauchy–Schwarz inequality $|\\langle u,v\\rangle|^2 \\leq \\langle u,u\\rangle\\langle v,v\\rangle$ holds in every inner product space and is the mathematical root of Heisenberg\'s uncertainty principle in physics',
    'Grothendieck\'s memoir "Récoltes et Semailles" describes twelve ideas he believed transformed mathematics; his concepts of toposes and motives remain active research frontiers today',
    'Taylor expansions represent smooth functions as power series — a tool at the heart of analysis and the rigorous foundation for engineering approximations like "small angle" in physics',
    'In mathematics, "isomorphism" and "equivalence" are distinct concepts: isomorphism preserves all structure, equivalence only some properties — confusing the two causes endless muddle',
    'Stirling\'s formula $n! \\approx \\sqrt{2\\pi n}(n/e)^n$ lets you compute large factorials without multiplying step by step; it appears in probability theory, statistical mechanics, and algorithm analysis',
    'Descartes introduced the coordinate system in 1637, translating geometric problems into algebraic equations — one of history\'s most influential "language translations" in mathematics',
    'Pólya\'s "How to Solve It" (1945) distilled problem-solving into four steps: understand, plan, execute, review — still the canonical reference for mathematical pedagogy eight decades later',
    'All of real analysis rests on completeness: Cauchy sequences in $\\mathbb{R}$ always converge, making limits, derivatives, and integrals rigorously definable',
    'RSA encryption relies on the difficulty of integer factorisation — but Shor\'s algorithm (1994) shows a quantum computer can factor large integers efficiently, threatening RSA once quantum hardware matures',
    'Convex optimisation is ubiquitous in machine learning: training a support vector machine is a convex quadratic program, which guarantees a globally optimal solution exists and is unique',
    'The infinite sum $1+1/2+1/4+1/8+\\cdots = 2$ confused ancient philosophers (Zeno\'s paradox) for centuries; rigorous limit theory in the 19th century finally provided a satisfying resolution',
    'Infinity has a hierarchy: $\\aleph_0 < 2^{\\aleph_0} < 2^{2^{\\aleph_0}} < \\cdots$ — Cantor\'s discovery that there are infinitely many levels of infinity shattered the intuition that "infinite means one size"',
    'One aesthetic criterion in mathematics is proof length — a one-line proof is often more admired than a thirty-page one, even when both are correct',
    'Lagrange multipliers let you optimise under constraints by converting the problem into an unconstrained extremum of an augmented function — a core tool in engineering and economics',
    '"Structural similarity" drives mathematical progress: defining rings, fields, and groups abstracts the essence of number operations so one theory simultaneously covers integers, polynomials, and rotations',
    'Constructive vs non-constructive proof: a constructive proof exhibits a specific object; a non-constructive proof (e.g. proof by contradiction) establishes existence without construction — the two camps still debate their merits',
    'Lebesgue integration replaced Riemann integration because it handles functions Riemann cannot (like the everywhere-discontinuous Dirichlet function) and satisfies far better limit theorems',
    'Poincaré recurrence theorem: in certain dynamical systems, almost every trajectory returns arbitrarily close to its starting point infinitely often — a closed physical system will "nearly" revisit its initial state given enough time',
    'In Solve mode, if you already know one step, state it explicitly: "assume Lemma X holds" — the AI will use that as a given and continue the derivation from there',
    'The birthday paradox: in a group of just 23 people, the probability that two share a birthday exceeds 50%. With 70 people it exceeds 99.9%. Our intuition severely underestimates coincidences in combinatorics',
    'Euler\'s identity $e^{i\\pi}+1=0$ unites five fundamental constants of mathematics in a single equation. In a poll of mathematicians it is consistently voted "the most beautiful formula"',
    'The axiom of choice seems obviously true (you can always pick one element from each non-empty set), yet it implies results like the Banach–Tarski paradox that feel deeply wrong — mathematics at its most paradoxical',
    'Category theory was initially dismissed as "abstract nonsense" by some mathematicians, but it became indispensable for organising and transferring ideas across wildly different areas of mathematics',
    'The Collatz conjecture: take any positive integer; if even, halve it; if odd, triple it and add 1; repeat. The conjecture says you always reach 1 — verified for every number up to $2^{68}$, yet unproved',
    'Sphere packing in 24 dimensions was solved by Maryna Viazovska in 2016 using modular forms — a stunning connection between a geometric optimisation problem and the analytic theory of automorphic forms',
    'The "unreasonable effectiveness of mathematics in natural science" (Wigner, 1960) remains one of philosophy\'s deepest puzzles: why should structures invented for pure abstraction describe physical reality so precisely?',
    'Gromov\'s h-principle shows that many geometric differential equations have solutions as long as there is no topological obstruction — topology constrains, but often less than you would expect',
    'The longest element in a finite Coxeter group corresponds to sending every positive root to a negative root; this single element captures a global symmetry of the entire root system',
    'Model theory studies the relationship between formal languages and the structures that satisfy them; a classical result is Löwenheim–Skolem: any first-order theory with an infinite model has models of every infinite cardinality',
    'The law of quadratic reciprocity, proved by Gauss at age 19, describes when one prime is a perfect square modulo another; Gauss called it the "gem of higher arithmetic" and gave eight different proofs',
    'Algebraic geometry connects polynomial equations to geometric shapes; Wiles\'s proof of Fermat\'s Last Theorem passes through the deep Shimura–Taniyama–Weil conjecture about elliptic curves and modular forms',
    'The sum of the first $n$ odd numbers is always $n^2$ — a fact with a beautiful visual proof: arrange dots in an L-shape, and each new odd number added forms the next perfect square',
  ],
};

// 页面加载时为每个用户独立洗牌一份副本，保证每次访问顺序不同
const _waitTipsShuffled = (() => {
  function _shuffle(arr) {
    const a = [...arr];
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }
  return { zh: _shuffle(_WAIT_TIPS.zh), en: _shuffle(_WAIT_TIPS.en) };
})();

let _waitTipTimer = null;
let _waitTipIdx = 0;
let _waitTipInterval = 8000;   // 固定 8 秒轮换间隔
let _waitTipAppearTimer = null; // 延迟出现的计时器
let _waitTipEl = null;

// PDF 审查进度等待提示（单独管理，不影响 solve 等待 tips）
let _rvWaitTipTimer = null;
let _rvWaitTipIdx = 0;

function _startReviewWaitTips(el) {
  if (!el) return;
  if (!AppState.settings.waitTips) return;
  if (_rvWaitTipTimer) clearInterval(_rvWaitTipTimer);
  const tips = _waitTipsShuffled[AppState.lang] || _waitTipsShuffled.zh;
  _rvWaitTipIdx = Math.floor(Math.random() * tips.length);

  // 延迟4秒后显示第一条提示
  setTimeout(() => {
    if (!AppState.settings.waitTips) return;
    if (!el.isConnected) return;
    el.innerHTML = _renderWaitTipText(tips[_rvWaitTipIdx]);
    renderKatexFallback(el);

    // 开始定时轮播
    _rvWaitTipTimer = setInterval(() => {
      if (!AppState.settings.waitTips) { _stopReviewWaitTips(null); return; }
      const ts = _waitTipsShuffled[AppState.lang] || _waitTipsShuffled.zh;
      _rvWaitTipIdx = (_rvWaitTipIdx + 1) % ts.length;
      if (el.isConnected) {
        el.innerHTML = _renderWaitTipText(ts[_rvWaitTipIdx]);
        renderKatexFallback(el);
      } else {
        _stopReviewWaitTips(null);
      }
    }, 9000);
  }, 4000);
}

function _stopReviewWaitTips(contentEl) {
  if (_rvWaitTipTimer) { clearInterval(_rvWaitTipTimer); _rvWaitTipTimer = null; }
  if (contentEl) {
    const el = contentEl.querySelector('#rv-wait-tip');
    if (el) el.textContent = '';
  }
}

function _renderMathText(text) {
  if (text === null || text === undefined) return '';
  const raw = normalizeEscapedNewlines(String(text)).trim();
  if (!raw) return '';
  try {
    const normalized = autoWrapMath(sanitizeLatex(raw));
    return escapeHtml(normalized).replace(/\n/g, '<br>');
  } catch {
    return escapeHtml(raw).replace(/\n/g, '<br>');
  }
}

function _inlineMathDelimiters(text) {
  if (!text) return text;
  const compactMath = (inner) => inner.replace(/\s+/g, ' ').trim();
  return text
    .replace(/\$\$([\s\S]*?)\$\$/g, (_, inner) => `$${compactMath(inner)}$`)
    .replace(/\\\[([\s\S]*?)\\\]/g, (_, inner) => `$${compactMath(inner)}$`)
    .replace(/\\\(([\s\S]*?)\\\)/g, (_, inner) => `$${compactMath(inner)}$`);
}

function _renderWaitTipText(text) {
  if (text === null || text === undefined) return '';
  const raw = _inlineMathDelimiters(normalizeEscapedNewlines(String(text)))
    .replace(/\s+/g, ' ')
    .trim();
  if (!raw) return '';
  try {
    const normalized = _inlineMathDelimiters(autoWrapMath(sanitizeLatex(raw)));
    return escapeHtml(normalized);
  } catch {
    return escapeHtml(raw);
  }
}

function _setWaitTipText(bar, text) {
  if (!bar) return;
  let txtEl = bar.querySelector('.wait-tip-text');
  if (!txtEl) {
    bar.innerHTML = '<span class="wait-tip-icon" aria-hidden="true">💡</span><span class="wait-tip-text"></span>';
    txtEl = bar.querySelector('.wait-tip-text');
  }
  txtEl.innerHTML = _renderWaitTipText(text);
}

function startWaitTips(containerEl, opts) {
  opts = opts || {};
  stopWaitTips();
  if (!AppState.settings.waitTips) return;
  if (_waitTipTimer || _waitTipAppearTimer) return;
  _waitTipIdx = Math.floor(Math.random() * (_waitTipsShuffled.en.length));
  _waitTipInterval = 9000;

  // 取当前语言的洗牌 tips（每次调用重新读，语言切换后自动生效）
  const getTips = () => _waitTipsShuffled[AppState.lang] || _waitTipsShuffled.en;

  const firstDelayMs = opts.firstDelayMs != null ? opts.firstDelayMs : 4000;

  // 延迟显示第一条（学习模式默认 800ms）
  _waitTipAppearTimer = setTimeout(() => {
    _waitTipAppearTimer = null;
    if (!AppState.settings.waitTips) return;
    const tips = getTips();

    const bar = document.createElement('div');
    bar.className = 'review-wait-tip';
    bar.dataset.waitTip = 'true';
    _setWaitTipText(bar, tips[_waitTipIdx % tips.length]);
    _waitTipEl = bar;
    containerEl.appendChild(bar);
    requestAnimationFrame(() => {
      renderKatexFallback(bar);
    });

        // 第一条出现后，按固定 9 秒间隔调度后续
    function scheduleNext() {
      _waitTipTimer = setTimeout(() => {
        _waitTipTimer = null;
        if (!AppState.settings.waitTips) return;
        const curTips = getTips();
        _waitTipIdx = (_waitTipIdx + 1) % curTips.length;
        const el = _waitTipEl;
        if (!el) return;
        _setWaitTipText(el, curTips[_waitTipIdx]);
        renderKatexFallback(el);
        scheduleNext();
      }, _waitTipInterval);
    }
    scheduleNext();
  }, firstDelayMs);
}

/**
 * 自动检测输入语言。
 * CJK 字符占非空格字符比例 > 10% → 'zh'，否则 'en'。
 */
function _detectLang(text) {
  if (AppState.lang) return AppState.lang;
  if (!text) return 'zh';
  const cjk = (text.match(/[一-鿿㐀-䶿＀-￯]/g) || []).length;
  const total = text.replace(/\s/g, '').length;
  return (cjk / Math.max(total, 1)) > 0.1 ? 'zh' : 'en';
}

function stopWaitTips() {
  if (_waitTipAppearTimer) { clearTimeout(_waitTipAppearTimer); _waitTipAppearTimer = null; }
  if (_waitTipTimer) { clearTimeout(_waitTipTimer); _waitTipTimer = null; }
  const el = _waitTipEl || document.querySelector('[data-wait-tip="true"]');
  _waitTipEl = null;
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

function updateConfigState(llm = {}, configPath = '') {
  const badge = document.getElementById('llm-config-state');
  const source = document.getElementById('llm-config-source');
  const configured = !!llm.api_key_configured;
  if (badge) {
    badge.textContent = configured ? t('panel.configKeyReady') : t('panel.configKeyMissing');
    badge.className = `config-state-badge ${configured ? 'ok' : 'unavailable'}`;
  }
  if (source) source.textContent = configPath || '';
}

function applyApiConfigVisibility(canConfigure) {
  document.querySelectorAll('.api-config-section').forEach(section => {
    section.style.display = canConfigure ? '' : 'none';
  });
}

function updateUserUi() {
  const user = AppState.user;
  const nameEl = document.getElementById('user-name-display');
  const quotaEl = document.getElementById('user-quota-display');
  if (nameEl) nameEl.textContent = user?.username || '';
  if (quotaEl && user) {
    quotaEl.textContent = user.quota_unlimited ? 'Quota ∞' : `Quota ${user.quota_remaining}/${user.quota_limit}`;
  }
}

function applyConfigToUi(cfg) {
  if (!cfg) return;
  AppState.config = cfg;
  applyApiConfigVisibility(cfg.auth?.can_configure_api !== false);
  if (cfg.user) {
    AppState.user = cfg.user;
    AppState.userId = cfg.user.id;
    updateUserUi();
  }
  if (cfg.settings && typeof cfg.settings.wait_tips === 'boolean') {
    AppState.settings.waitTips = cfg.settings.wait_tips;
    const waitTipsToggle = document.getElementById('toggle-wait-tips');
    if (waitTipsToggle) waitTipsToggle.checked = AppState.settings.waitTips;
  }
  const llm = cfg.llm || {};
  const baseEl = document.getElementById('input-llm-base-url');
  const modelEl = document.getElementById('input-llm-model');
  if (baseEl) baseEl.value = llm.base_url || '';
  if (modelEl) modelEl.value = llm.model || '';
  if (llm.model) setActiveModel(llm.model);
  updateConfigState(llm, cfg.config_path || '');
}

async function loadAppConfig() {
  try {
    const cfg = await apiFetch('/config');
    applyConfigToUi(cfg);
    return cfg;
  } catch (err) {
    const badge = document.getElementById('llm-config-state');
    const source = document.getElementById('llm-config-source');
    if (badge) {
      badge.textContent = t('panel.configUnknown');
      badge.className = 'config-state-badge unknown';
    }
    if (source) source.textContent = '';
    console.warn('Config load failed', err);
    return null;
  }
}

async function authMe() {
  return apiFetch('/auth/me');
}

async function refreshCurrentUser() {
  try {
    const data = await authMe();
    AppState.user = data.user;
    AppState.userId = data.user?.id || AppState.userId;
    updateUserUi();
  } catch {}
}

function showAuth(errorText = '') {
  document.getElementById('auth-view')?.style && (document.getElementById('auth-view').style.display = 'flex');
  document.getElementById('app-shell')?.style && (document.getElementById('app-shell').style.display = 'none');
  const errEl = document.getElementById('auth-error');
  if (errEl) errEl.textContent = errorText || '';
}

function showAppShell() {
  document.getElementById('auth-view')?.style && (document.getElementById('auth-view').style.display = 'none');
  document.getElementById('app-shell')?.style && (document.getElementById('app-shell').style.display = '');
}

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
function addMessageActions(bubbleEl, rawText, opts = {}) {
  if (!bubbleEl) return;
  bubbleEl.querySelector('.msg-actions')?.remove();

  const actionsEl = document.createElement('div');
  actionsEl.className = 'msg-actions';
  const latexBtnHtml = opts.isSolve
    ? `<button class="msg-action-btn msg-latex-btn" onclick="triggerLatexFromBubble(this)"
         title="${t('ui.latexBtnTitle')}">{ } LaTeX</button>`
    : '';
  const regenerateBtnHtml = `<button class="msg-action-btn msg-regenerate-btn" onclick="regenerateMessage(this)"
         title="${t('ui.regenerate')}">↻ ${t('ui.regenerate')}</button>`;
  actionsEl.innerHTML = `
    ${regenerateBtnHtml}
    <button class="msg-action-btn" onclick="copyMsgText(this)">⎘ ${t('ui.copy')}</button>
    ${latexBtnHtml}
  `;
  actionsEl.dataset.rawText = rawText;
  bubbleEl.appendChild(actionsEl);
}

window.triggerLatexFromBubble = function(btn) {
  if (btn.dataset.running === 'true') return;  // 防重入
  const bubble = btn.closest('.msg-bubble');
  const contentEl = bubble?.querySelector('.msg-content');
  const blueprint = contentEl?.dataset.solveBlueprint;
  const statement = contentEl?.dataset.solveStatement || '';
  if (!blueprint) {
    showToast('warning', t('ui.latexNoBlueprintHint'));
    return;
  }
  btn.dataset.running = 'true';
  btn.textContent = `{ } ${t('ui.latexGenerating')}`;
  btn.disabled = true;

  _streamLatexPanel(contentEl, blueprint, statement)
    .catch(err => { if (err?.name !== 'AbortError') showToast('error', err.message || String(err)); })
    .finally(() => {
      btn.dataset.running = 'false';
      btn.disabled = false;
      btn.textContent = '{ } LaTeX';
    });
};

window.copyMsgText = function(btn) {
  const raw = btn.closest('.msg-actions')?.dataset.rawText || '';
  navigator.clipboard.writeText(raw).then(() => {
    btn.textContent = `✓ ${t('ui.copied')}`;
    btn.classList.add('copied');
    setTimeout(() => { btn.innerHTML = `⎘ ${t('ui.copy')}`; btn.classList.remove('copied'); }, 2000);
  }).catch(() => showToast('error', t('ui.err.copyFailed')));
};

window.regenerateMessage = function(btn) {
  if (!_lastAttempt) {
    showToast('warning', AppState.lang === 'zh' ? '无法重新生成：缺少上下文' : 'Cannot regenerate: missing context');
    return;
  }

  if (AppState.isStreaming) {
    showToast('warning', AppState.lang === 'zh' ? '请等待当前生成完成' : 'Please wait for current generation to complete');
    return;
  }

  const { mode, statement, proofText, level, lang, model, attachments } = _lastAttempt;

  const bubbleEl = btn.closest('.msg-bubble');
  const contentEl = bubbleEl?.querySelector('.msg-content');
  if (!bubbleEl || !contentEl) {
    showToast('warning', AppState.lang === 'zh' ? '无法重新生成：目标消息不存在' : 'Cannot regenerate: target message missing');
    return;
  }
  bubbleEl.querySelector('.msg-actions')?.remove();
  contentEl.innerHTML = makeThinkingInnerHtml(t('ui.thinking'));
  contentEl.removeAttribute('data-solve-blueprint');
  contentEl.removeAttribute('data-solve-statement');
  _regenerateTargetContentEl = contentEl;

  // 恢复模式和模型
  AppState.set('mode', mode);
  if (model) {
    setActiveModel(model);
  }

  // 根据不同模式恢复参数
  if (mode === 'learning' && level !== undefined) {
    // 恢复learning模式的level参数
    AppState.settings.level = level;
    // 同步UI（如果有level选择器的话）
    const levelSelect = document.getElementById('input-level');
    if (levelSelect) levelSelect.value = level;
  }

  if (mode === 'reviewing') {
    // 对于reviewing模式，需要提示用户无法直接恢复附件
    if (attachments && attachments.length > 0) {
      showToast('info', AppState.lang === 'zh'
        ? '提示：PDF附件无法自动恢复，请重新上传'
        : 'Note: PDF attachments cannot be auto-restored, please re-upload');
    }
    const ta = document.getElementById('input-textarea');
    if (ta && proofText) {
      ta.value = proofText;
      autoResize(ta);
    }
  } else if (statement) {
    // 其他模式恢复statement
    const ta = document.getElementById('input-textarea');
    if (ta) {
      ta.value = statement;
      autoResize(ta);
    }
  }

  _isRegenerating = true;  // 设置重新生成标志
  sendMessage();
};


function makeThinkingInnerHtml(message) {
  const msg = message || t('ui.thinking');
  return `<div class="thinking-trace"><div class="thinking-step active">
    <span class="step-dot pulsing"></span>
    <span class="step-msg">${escapeHtml(msg)}</span>
  </div></div>`;
}

function makeThinkingHtml(message) {
  return `<div class="msg-content">${makeThinkingInnerHtml(message)}</div>`;
}

function addMessage(role, content, opts = {}) {
  // 重新生成时跳过添加用户消息（避免重复显示）
  if (role === 'user' && _isRegenerating) {
    return null;
  }

  if (role === 'ai' && _isRegenerating) {
    const target = takeRegenerateTargetContentEl();
    if (target) {
      const lastHistory = AppState.history[AppState.history.length - 1];
      if (lastHistory && lastHistory.role === 'ai') lastHistory.content = '';
      target.innerHTML = content ? renderMarkdown(content) : makeThinkingInnerHtml(t('ui.thinking'));
      target.scrollIntoView({ block: 'end', behavior: 'smooth' });
      return target;
    }
  }

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

  // PDF attachment chips（仅用户消息）
  if (opts.pdfAttachments?.length) {
    const chipsRow = document.createElement('div');
    chipsRow.className = 'msg-pdf-chips';
    chipsRow.innerHTML = opts.pdfAttachments.map((att, i) => {
      const pageStr = att.pageCount ? ` · ${att.pageCount} 页` : '';
      return `<div class="msg-pdf-chip"
                   data-att-idx="${i}"
                   data-name="${escapeHtml(att.name || '')}"
                   data-pages="${att.pageCount || ''}"
                   data-url="${escapeHtml(att.objectUrl || '')}">
        <span class="msg-pdf-chip-icon">📕</span>
        <span class="msg-pdf-chip-name" title="${escapeHtml(att.name || '')}">${escapeHtml(att.name || '')}</span>
        ${pageStr ? `<span class="msg-pdf-chip-pages">${pageStr}</span>` : ''}
      </div>`;
    }).join('');
    contentEl.appendChild(chipsRow);

    // 绑定 hover / click，thumbnails 不写进 DOM（避免 HTML 膨胀）
    chipsRow.querySelectorAll('.msg-pdf-chip').forEach((chip, i) => {
      const att = opts.pdfAttachments[i];
      chip.addEventListener('mouseenter', () => {
        if (att.thumbnails?.length) _showPdfThumbTooltip(chip, att.thumbnails);
      });
      chip.addEventListener('mouseleave', _hidePdfThumbTooltip);
      chip.addEventListener('click', () => {
        openPdfGallery(att.thumbnails, att.name, att.pageCount, att.objectUrl || null);
      });
    });
  }

  if (content) {
    const textDiv = document.createElement('div');
    textDiv.innerHTML = role === 'user'
      ? renderUserMessageHtml(content)
      : renderMarkdown(content);
    contentEl.appendChild(textDiv);
    if (role === 'ai' && !opts.noSave) {
      setTimeout(() => addMessageActions(bubble, content), 50);
    }
    setTimeout(() => renderKatexFallback(contentEl), 30);
  } else if (role === 'ai' && !opts.pdfAttachments?.length) {
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

  if (!opts.noSave) AppState.history.push({
    role, content: content || '', ts: Date.now(),
    pdfAttachments: opts.pdfAttachments?.length ? opts.pdfAttachments.map(a => ({
      name: a.name,
      pageCount: a.pageCount,
      thumbnails: a.thumbnails || [],
      // objectUrl 是 blob URL，不持久化
    })) : undefined,
  });
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
let _isRegenerating = false;  // 标志：是否正在重新生成（避免重复显示用户消息）
let _regenerateTargetContentEl = null;

function takeRegenerateTargetContentEl() {
  const el = _regenerateTargetContentEl;
  _regenerateTargetContentEl = null;
  return el && el.isConnected ? el : null;
}

window.retryLastMessage = function() {
  if (!_lastAttempt) return;
  const { mode, statement, proofText } = _lastAttempt;
  const contentEl = document.querySelector('.msg-error .msg-error-retry')?.closest('.msg-content') || null;
  if (contentEl) {
    contentEl.innerHTML = makeThinkingInnerHtml(t('ui.thinking'));
    _regenerateTargetContentEl = contentEl;
  }
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
  _isRegenerating = true;  // 设置重新生成标志
  sendMessage();
};

/* ─────────────────────────────────────────────────────────────
   13. 模式处理器 · 学习模式辅助
───────────────────────────────────────────────────────────── */
const LEARN_SECTION_ORDER = ['background', 'prereq', 'proof', 'examples', 'extensions'];
const LEARN_SECTION_ICONS = { background: '◉', prereq: '◔', proof: '◧', examples: '◑', extensions: '◐' };

function _makeSkeletonHtml() {
  const hint = escapeHtml(t('ui.learn.generatingHint'));
  return `<div class="section-skeleton" aria-live="polite"><span class="skeleton-line"></span><span class="skeleton-line short"></span><span class="skeleton-hint">${hint}</span></div>`;
}

function buildLearnSkeletonHtml() {
  const ORDER = LEARN_SECTION_ORDER.slice(0, 4);
  const skel = _makeSkeletonHtml();
  return ORDER.map(key => `
    <details class="accordion learn-section" data-section="${key}" open>
      <summary>
        <span class="accordion-section-icon">${LEARN_SECTION_ICONS[key]}</span>
        <span class="accordion-label">${escapeHtml(t('ui.accordion.' + key))}</span>
        <span class="section-status section-status-pending">${escapeHtml(t('ui.learn.statusPending'))}</span>
      </summary>
      <div class="accordion-body">${skel}</div>
    </details>`).join('');
}

function _setLearnSectionStatus(sectionId, state, detailMsg, root = document) {
  const el = root.querySelector(`.learn-body [data-section="${sectionId}"] .section-status`);
  if (!el) return;
  el.className = 'section-status section-status-' + state;
  if (state === 'running' && detailMsg) {
    el.textContent = detailMsg;
    return;
  }
  const map = {
    pending: 'ui.learn.statusPending',
    running: 'ui.learn.statusRunning',
    done: 'ui.learn.statusDone',
    error: 'ui.learn.statusError',
  };
  el.textContent = t(map[state] || map.pending);
}

function _applyLearningSectionsToDom(sections, root = document) {
  if (!sections) return;
  for (const key of LEARN_SECTION_ORDER) {
    const sec = sections[key];
    if (!sec || !String(sec.content || '').trim()) continue;
    if (String(sec.content).includes('section-skeleton')) continue;
    const body = root.querySelector(`.learn-body [data-section="${key}"] .accordion-body`);
    if (body) {
      body.innerHTML = renderMarkdown(sec.content);
      renderKatexFallback(body);
    }
  }
}

function rebuildLearningMarkdown(sections) {
  if (!sections) return '';
  const parts = [];
  for (const k of LEARN_SECTION_ORDER) {
    const s = sections[k];
    if (!s || !String(s.content || '').trim()) continue;
    if (String(s.content).includes('section-skeleton')) continue;
    const title = (s.title || '').trim() || k;
    parts.push(`## ${title}\n\n${String(s.content).trim()}`);
  }
  return parts.length ? parts.join('\n\n') + '\n' : '';
}

function stripLearningThinkingLeak(text) {
  if (!text) return text;
  let out = String(text);
  let prev = null;
  const blockRe = /^\s*(?:<think>[\s\S]*?<\/think>\s*|(?:thinking|reasoning|analysis|chain[- ]of[- ]thought|internal reasoning)\s*:\s*[\s\S]*?(?:\n\s*\n|$))/i;
  while (out !== prev) {
    prev = out;
    out = out.replace(blockRe, '').trimStart();
  }
  if (!/^\s*(?:crafting|i need to|i should|i will|i'm thinking|i am thinking|let me|we need to craft|need to create|plan:|approach:|analysis:|reasoning:)\b/i.test(out)) {
    return out;
  }
  const startRe = /^(?:策略|证明思路|思路|首先|我们|为了|下面|记|设|令|证明|例|背景|从|在|这个|该|strategy|proof|we|to prove|first|let|suppose|assume|consider|example|background|historically|\*\*Step\s+\d+\*\*|Step\s+\d+|###\s+Example\s+\d+)/im;
  const m = startRe.exec(out);
  if (m && m.index > 0) return out.slice(m.index).trimStart();
  const parts = out.split(/\n\s*\n/);
  if (parts.length > 1 && parts[0].length < 1200) return parts.slice(1).join('\n\n').trimStart();
  return out;
}

function _renderLearnSectionError(sectionId, message, root = document) {
  _setLearnSectionStatus(sectionId, 'error', undefined, root);
  const body = root.querySelector(`.learn-body [data-section="${sectionId}"] .accordion-body`);
  if (!body) return;
  const msg = escapeHtml(message || '');
  const fail = escapeHtml(t('ui.learn.sectionFailed'));
  const btnLabel = escapeHtml(t('ui.learn.retrySection'));
  body.innerHTML = `<div class="section-error" role="alert">
    <span class="section-error-icon">!</span>
    <div class="section-error-text">${fail} ${msg}</div>
    <button type="button" class="section-retry-btn">${btnLabel}</button>
  </div>`;
  const btnEl = body.querySelector('.section-retry-btn');
  if (btnEl) btnEl.addEventListener('click', () => retryLearnSection(sectionId));
}

window.retryLearnSection = async function(sectionId) {
  const ctx = window._lastLearnContext;
  if (!ctx || !sectionId) return;
  // 防止同一节同时发起多个重试请求
  if (retryLearnSection._running && retryLearnSection._running === sectionId) return;
  retryLearnSection._running = sectionId;
  _setLearnSectionStatus(sectionId, 'running', t('ui.learn.statusRunning'));
  const root = window._lastLearnContentEl || document;
  const body = root.querySelector(`.learn-body [data-section="${sectionId}"] .accordion-body`);
  if (body) {
    body.innerHTML = _makeSkeletonHtml();
  }
  let retryRaw = '';
  try {
    const resp = await fetch('/learn/section', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        statement: ctx.statement,
        section: sectionId,
        level: ctx.level,
        model: ctx.model,
        lang: ctx.lang,
      }),
      signal: AppState._abortController ? AppState._abortController.signal : undefined,
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
            const cleanChunk = obj.chunk
              .replace(/<!--(?!vp-)[^>]*-->/g, '')
              // 先处理完整的 \[ ... \] 块
              .replace(/\\\[([\s\S]*?)\\\]/g, '$$$$1$$')
              // 再处理孤立的 \[ 或 \]（可能是混合情况）
              .replace(/\\\[/g, '$$')
              .replace(/\\\]/g, '$$')
              // 修复混合定界符：$ ... \] 或 \[ ... $
              .replace(/\$([^\$]*?)\\\]/g, '$$$$1$$')
              .replace(/\\\[([^\$]*?)\$/g, '$$$$1$$');
            retryRaw += cleanChunk;
            const one = parseLearningOutput(retryRaw);
            if (one && one[sectionId] && !String(one[sectionId].content).includes('section-skeleton')) {
              const bodyEl = root.querySelector(`.learn-body [data-section="${sectionId}"] .accordion-body`);
              if (bodyEl) {
                bodyEl.innerHTML = renderMarkdown(one[sectionId].content);
                renderKatexFallback(bodyEl);
              }
            }
          } else if (obj.section_error) {
            _renderLearnSectionError(obj.section_error.id, obj.section_error.message, root);
            return;
          } else if (obj.error) {
            throw new Error(obj.error);
          }
        } catch (parseErr) {
          if (parseErr.message && parseErr.message !== raw) throw parseErr;
        }
      }
    }
    const prev = parseLearningOutput(window._lastLearnRawBuffer || '') || {};
    const neu = parseLearningOutput(retryRaw) || {};
    if (neu[sectionId]) prev[sectionId] = neu[sectionId];
    window._lastLearnRawBuffer = rebuildLearningMarkdown(prev);
    const lastHistory = AppState.history[AppState.history.length - 1];
    if (lastHistory && lastHistory.role === 'ai') lastHistory.content = window._lastLearnRawBuffer;
    if (window._lastLearnBubbleEl) addMessageActions(window._lastLearnBubbleEl, window._lastLearnRawBuffer);
    _setLearnSectionStatus(sectionId, 'done', undefined, root);
  } catch (err) {
    _renderLearnSectionError(sectionId, err.message || String(err), root);
    showToast('error', err.message || String(err));
  } finally {
    retryLearnSection._running = null;
  }
};

/* ─────────────────────────────────────────────────────────────
   13. 模式处理器
───────────────────────────────────────────────────────────── */
async function handleLearning(statement) {
  const level = AppState.settings.level;
  const lang = AppState.lang === 'zh' ? 'zh' : AppState.lang === 'en' ? 'en' : _detectLang(statement);
  const model = AppState.model;

  // 保存完整请求参数以支持重新生成
  _lastAttempt = {
    mode: 'learning',
    statement,
    level,
    lang,
    model
  };

  // 界面语言优先：中文 UI 下前置知识等内容统一中文，避免仅用题干语种误判为英文
  window._lastLearnContext = {
    statement,
    level,
    lang,
    model,
  };
  addMessage('user', statement);
  const contentEl = addMessage('ai', null);
  if (!contentEl) return;
  window._lastLearnContentEl = contentEl;

  contentEl.innerHTML = `<div class="learn-body">${buildLearnSkeletonHtml()}</div>`;
  AppState.set('isStreaming', true);

  startWaitTips(contentEl, { firstDelayMs: 800 });

  const ctrl = new AbortController();
  AppState._abortController = ctrl;

  const bodyEl = () => contentEl.querySelector('.learn-body');

  let rawBuffer = '';

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
        lang,
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
            const cleanChunk = obj.chunk
              .replace(/<!--(?!vp-)[^>]*-->/g, '')
              // 先处理完整的 \[ ... \] 块
              .replace(/\\\[([\s\S]*?)\\\]/g, '$$$$1$$')
              // 再处理孤立的 \[ 或 \]（可能是混合情况）
              .replace(/\\\[/g, '$$')
              .replace(/\\\]/g, '$$')
              // 修复混合定界符：$ ... \] 或 \[ ... $
              .replace(/\$([^\$]*?)\\\]/g, '$$$$1$$')
              .replace(/\\\[([^\$]*?)\$/g, '$$$$1$$');
            rawBuffer += cleanChunk;
            const sections = parseLearningOutput(rawBuffer, { allowEmpty: true });
            if (bodyEl()) _applyLearningSectionsToDom(sections, contentEl);
          } else if (obj.step !== undefined && obj.status !== undefined) {
            const st = obj.step;
            const msg = obj.status;
            const order = LEARN_SECTION_ORDER.slice(0, 4);
            if (st === 'done') {
              order.forEach(k => _setLearnSectionStatus(k, 'done', undefined, contentEl));
            } else {
              const idx = order.indexOf(st);
              if (idx >= 0) {
                for (let i = 0; i < idx; i++) _setLearnSectionStatus(order[i], 'done', undefined, contentEl);
                _setLearnSectionStatus(st, 'running', msg, contentEl);
              }
            }
          } else if (obj.section_error) {
            _renderLearnSectionError(obj.section_error.id, obj.section_error.message, contentEl);
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
      // 用户主动停止：仅关闭流式状态，不将半成品标记为完成或写入历史
      AppState.set('isStreaming', false);
      stopWaitTips();
      return;
    } else {
      AppState.set('isStreaming', false);
      addErrorInline(contentEl, t('ui.err.learning', { e: err.message || err }));
      showToast('error', err.message || String(err));
      stopWaitTips();
      return;
    }
  }

  AppState.set('isStreaming', false);

  const b = bodyEl();
  if (b) {
    // 折叠流式期间全部展开的非默认节(但保持examples展开,根据用户需求)
    ['prereq', 'extensions'].forEach(k => {
      b.querySelector(`[data-section="${k}"]`)?.removeAttribute('open');
    });
    // 确保 examples 保持展开（用户反馈）
    const examplesEl = b.querySelector('[data-section="examples"]');
    if (examplesEl) examplesEl.setAttribute('open', '');
    // 确保所有状态徽章显示"完成"；若某节仍是骨架占位，改为"无内容"空状态
    const isZh = AppState.lang === 'zh';
    ['background', 'prereq', 'proof', 'examples'].forEach(k => {
      const secEl = b.querySelector(`[data-section="${k}"]`);
      const body = secEl?.querySelector('.accordion-body');
      const hasRealContent = body && !body.querySelector('.section-skeleton') && body.textContent.trim().length > 0;
      if (!hasRealContent && body && body.querySelector('.section-skeleton')) {
        // 骨架占位 → 改为「本节未返回内容」空状态
        body.innerHTML = `<p class="section-empty-hint">${isZh ? '本节内容未生成，可点击「重新生成」重试。' : 'No content generated. Click "Regenerate" to retry.'}</p>`;
        _setLearnSectionStatus(k, 'error', undefined, contentEl);
      } else {
        _setLearnSectionStatus(k, 'done', undefined, contentEl);
      }
    });
    // 最终 KaTeX 兜底渲染
      renderKatexFallback(b);
  }

  window._lastLearnRawBuffer = rawBuffer;
  const bubbleEl = contentEl.closest('.msg-bubble');
  window._lastLearnBubbleEl = bubbleEl || null;
  if (bubbleEl) addMessageActions(bubbleEl, rawBuffer);

  stopWaitTips();

  const lastHistory = AppState.history[AppState.history.length - 1];
  if (lastHistory && lastHistory.role === 'ai' && !lastHistory.content) {
    lastHistory.content = rawBuffer || '';
  }
  saveCurrentSession(statement);
  refreshCurrentUser().catch(() => {});
  smartScroll(contentEl);
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
    let content = text.slice(bodyStart, bodyEnd).trim();
    if (!content) {
      if (!allowEmpty) return;
      // plan F.3 (T55)：流式空段不再用单薄的 "..."，改为可读的等待提示 + 微动画占位骨架
      const hint = t('ui.learn.generatingHintDetailed');
      content = `<div class="section-skeleton" aria-live="polite"><span class="skeleton-line"></span><span class="skeleton-line short"></span><span class="skeleton-hint">${hint}</span></div>`;
    }

    const titleLower = h.title.toLowerCase();
    const def = PATTERNS.find(p => p.words.some(w => titleLower.includes(w.toLowerCase())));
    if (!def) return;

    if (sections[def.key]) {
      sections[def.key].content += '\n\n' + stripLearningThinkingLeak(content);
    } else {
      sections[def.key] = { title: h.title, content: stripLearningThinkingLeak(content) };
    }
  });

  return Object.keys(sections).length > 0 ? sections : null;
}

function buildAccordionHtml(sections, opts) {
  if (!sections) return '';
  opts = opts || {};
  // 流式期间所有 section 默认展开，让用户实时看到生成；最终态保持 prereq+proof 展开，其余可折叠
  const expandAll = !!opts.expandAll || AppState.isStreaming;

  const LABELS = {
    background: t('ui.accordion.background'),
    prereq:     t('ui.accordion.prereq'),
    proof:      t('ui.accordion.proof'),
    examples:   t('ui.accordion.examples'),
    extensions: t('ui.accordion.extensions'),
  };

  return LEARN_SECTION_ORDER
    .filter(key => sections[key] && sections[key].content.trim())
    .map(key => {
      const { content } = sections[key];
      const label   = LABELS[key];
      const icon    = LEARN_SECTION_ICONS[key];
      const bodyHtml = renderMarkdown(content);
      const open = expandAll || key === 'proof' || key === 'background' || key === 'examples' ? 'open' : '';
      // 每个 accordion body 在插入 DOM 后需要触发 KaTeX 渲染，用 data 属性标记
      return `
        <details class="accordion learn-section" data-section="${key}" ${open} data-needs-katex="1">
          <summary>
            <span class="accordion-section-icon">${icon}</span><span class="accordion-label">${label}</span>
          </summary>
          <div class="accordion-body">${bodyHtml}</div>
        </details>`;
    }).join('');
}

async function handleSolving(statement) {
  const model = AppState.model;
  // 保存完整请求参数以支持重新生成
  _lastAttempt = {
    mode: 'solving',
    statement,
    model
  };
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
          // 只吞掉 JSON.parse 产生的 SyntaxError；其他错误（如 obj.error 触发的抛出）向上传
          if (!(parseErr instanceof SyntaxError)) throw parseErr;
        }
      }
    }
  } catch (err) {
    if (err && err.name === 'AbortError') {
      _finalizeSolve(contentEl, rawBuffer, metadata, statement, true);
      return;
    }
    AppState.set('isStreaming', false);
    stopWaitTips();
    addErrorInline(contentEl, t('ui.err.solving', { e: err.message || err }));
    showToast('error', err.message || String(err));
    return;
  }

  _finalizeSolve(contentEl, rawBuffer, metadata, statement, false);
}

function _buildSolveShell() {
  return `
    <div class="solve-status-pill">
      <span class="spinner" aria-hidden="true"></span>
      <span class="solve-status-text">${t('ui.solveStarting')}</span>
    </div>
    <div class="solve-steps"></div>
    <div class="solve-layout">
      <div class="solve-body"></div>
      <div class="solve-latex-panel" style="display:none">
        <div class="solve-latex-header">
          <span class="solve-latex-title">LaTeX</span>
          <div class="solve-latex-actions">
            <span class="solve-latex-status"></span>
            <button class="solve-latex-copy-btn" title="${t('ui.copy')} LaTeX">${t('ui.copy')}</button>
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
    if (txt) txt.textContent = stopped ? t('ui.solveStopped') : t('ui.solveDone');
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
    // 提取 metadata（置信度、判定、引用）并渲染 verdict bar
    extractSolveMetadata(rawBuffer, metadata);
    // 有置信度或非默认判定时显示 verdict bar
    if (metadata.verdict && (metadata.verdict !== 'unproven' || metadata.confidence > 0)) {
      const barHtml = buildVerdictBar(metadata);
      bodyEl.innerHTML = barHtml + renderMarkdown(rawBuffer);
    } else {
    bodyEl.innerHTML = renderMarkdown(rawBuffer);
    }
    renderKatexFallback(bodyEl);
  }

  // 存储 blueprint 和 statement 供气泡 { } LaTeX 按钮使用
  if (rawBuffer) contentEl.dataset.solveBlueprint = rawBuffer;
  contentEl.dataset.solveStatement = statement;

  // 添加操作按钮（含 { } LaTeX 按钮）
  const bubbleEl = contentEl.closest('.msg-bubble');
  if (bubbleEl) addMessageActions(bubbleEl, rawBuffer, { isSolve: true });

  // 存历史
  const lastHistory = AppState.history[AppState.history.length - 1];
  if (lastHistory && lastHistory.role === 'ai' && !lastHistory.content) {
    lastHistory.content = rawBuffer || '';
  }
  saveCurrentSession(statement);
  refreshCurrentUser().catch(() => {});
  smartScroll(contentEl);
}

async function _streamLatexPanel(contentEl, blueprint, statement = '') {
  const panel = contentEl.querySelector('.solve-latex-panel');
  if (!panel) return;
  panel.style.display = '';

  const codeEl = panel.querySelector('code');
  const statusEl = panel.querySelector('.solve-latex-status');
  const copyBtn = panel.querySelector('.solve-latex-copy-btn');

  if (statusEl) statusEl.textContent = t('ui.latexGenerating');

  // Strip markdown code fences so the output is directly pasteable into Overleaf
  const _stripFences = s => s
    .replace(/^```(?:latex|tex)?\s*\n?/i, '')
    .replace(/\n?```\s*$/i, '')
    .trim();

  let latex = '';

  // 用 cloneNode 替换旧按钮，避免多次调用时监听器叠加
  if (copyBtn) {
    const freshCopyBtn = copyBtn.cloneNode(true);
    copyBtn.parentNode.replaceChild(freshCopyBtn, copyBtn);
    freshCopyBtn.addEventListener('click', () => {
    if (!latex) return;
    const clean = _stripFences(latex);
    navigator.clipboard.writeText(clean).then(() => {
        const prev = freshCopyBtn.textContent;
        freshCopyBtn.textContent = t('ui.latexCopied');
        setTimeout(() => { freshCopyBtn.textContent = prev; }, 1500);
    }).catch(() => {
      const ta = document.createElement('textarea');
      ta.value = clean;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    });
  });
  }

  try {
    const resp = await fetch('/solve_latex', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ blueprint, statement, model: AppState.model }),
    });
    if (!resp.ok) {
      let detail = `HTTP ${resp.status}`;
      try { const e = await resp.json(); detail = e.detail || e.error?.message || detail; } catch {}
      throw new Error(detail);
    }

    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    let buf = '';
    let hasError = false;

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
          } else if (obj.error) {
            if (statusEl) statusEl.textContent = t('ui.latexError', { e: obj.error });
            hasError = true;
            break;
          }
        } catch {}
      }
      if (hasError) break;
    }

    if (!hasError) {
      if (statusEl) statusEl.textContent = t('ui.latexDone');
      // freshCopyBtn 已替换 copyBtn，用 panel 重新查询
      const activeCopyBtn = panel.querySelector('.solve-latex-copy-btn');
      if (activeCopyBtn) activeCopyBtn.disabled = false;

      // Overleaf 提示（移除旧的，插入新的）
      panel.querySelector('.solve-overleaf-note')?.remove();
    const noteEl = document.createElement('div');
    noteEl.className = 'solve-overleaf-note';
      noteEl.innerHTML = t('ui.latexOverleafHtml');
    panel.appendChild(noteEl);
    }
  } catch (e) {
    if (statusEl) statusEl.textContent = t('ui.latexError', { e: e.message });
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

  const memHtml = (meta.memCount > 0)
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
  const s = normalizeEscapedNewlines(String(text)).trim();
  if (!s) return '';
  try {
    if (typeof marked === 'undefined') {
      return escapeHtml(s).replace(/\n/g, '<br>');
    }
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
  let s = sanitizeLatex(normalizeEscapedNewlines(text));
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
  // 末尾用 (?![a-zA-Z]) 替代 \b，使 \chi_\sigma 这类「命令+下标」也能被包进 $...$
  s = s.replace(/(?<![\\$\w])(\\(?:frac|sqrt|sum|prod|int|lim|sup|inf|mathbb|mathcal|mathfrak|mathrm|mathbf|mathit|operatorname|forall|exists|in|notin|subset|subseteq|cup|cap|leq|geq|neq|to|mapsto|mid|alpha|beta|gamma|delta|epsilon|varepsilon|zeta|eta|theta|vartheta|iota|kappa|lambda|mu|nu|xi|pi|rho|sigma|tau|upsilon|phi|varphi|chi|psi|omega|Gamma|Delta|Theta|Lambda|Xi|Pi|Sigma|Phi|Psi|Omega|infty|partial|nabla|cdot|cdots|ldots|times|div|pm|mp|approx|equiv|sim|propto|circ|prime)(?:\{[^{}]*\}|(?![a-zA-Z])))/g,
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
  const raw = normalizeEscapedNewlines(String(text)).trim();
  if (!raw) return '';

  // 检查是否包含HTML标签（表格等）
  const hasHtmlTags = /<(table|thead|tbody|tr|td|th|div|p|span|ul|ol|li)[\s>]/i.test(raw);

  if (hasHtmlTags) {
    // 包含HTML标签，使用 marked 渲染（支持表格和Markdown）
    try {
      let rendered = renderMarkdown(raw);
      // 确保 LaTeX 公式被渲染
      return rendered;
    } catch (err) {
      console.warn('renderMathText: marked rendering failed', err);
    }
  }

  // 普通文本路径
  let normalized = raw;
  try {
    normalized = autoWrapReviewMath(raw);
  } catch {}

  // 保护多行 $$...$$ 块，避免被 \n{2,} 段落分割拆散导致单侧定界符丢失
  const mathBlocks = [];
  normalized = normalized.replace(/\$\$[\s\S]*?\$\$/g, m => {
    mathBlocks.push(m);
    return `\x00MB${mathBlocks.length - 1}\x00`;
  });

  const safe = escapeHtml(normalized);
  if (inline) return safe.replace(/\s*\n+\s*/g, ' ');

  const blocks = safe
    .split(/\n{2,}/)
    .map(part => part.trim())
    .filter(Boolean)
    .map(part => {
      // 还原 $$...$$ 占位符（在 escapeHtml 之后，占位符本身不含特殊字符，不受影响）
      const restored = part.replace(/\x00MB(\d+)\x00/g, (_, i) => mathBlocks[+i]);
      return `<p class="review-math-paragraph">${restored.replace(/\n/g, '<br>')}</p>`;
    });
  return blocks.join('') || (() => {
    const restored = safe.replace(/\x00MB(\d+)\x00/g, (_, i) => mathBlocks[+i]);
    return `<p class="review-math-paragraph">${restored.replace(/\n/g, '<br>')}</p>`;
  })();
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
  const raw = stripPresentationMarkdown(normalizeEscapedNewlines(String(text)).trim());
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

/** severity/issue_type 字符串 → issue-level CSS class */
function _issueLevelCls(level) {
  const l = (level || '').toLowerCase().replace(/[^a-z_]/g, '');
  if (['critical', 'high', 'error', 'critical_error'].includes(l)) return 'critical';
  if (['medium', 'warning', 'gap'].includes(l)) return 'medium';
  if (['passed', 'correct', 'verified'].includes(l)) return 'passed';
  return 'info';
}

const _VERDICT_CSS_MAP = {
  'Correct': 'proved',
  'Minor Issues': 'partial',
  'Major Issues': 'partial',
  'Partial': 'partial',
  'Incorrect': 'unproven',
  'NotChecked': 'unproven',
  'Unverifiable': 'refused',
  'Error': 'refused',
};

function renderTheoremCardHtml(tr, index) {
  if (!tr) return '';
  const tCls = _VERDICT_CSS_MAP[tr.verdict] || 'unproven';
  // 内部 LLM 指令以 "(" 开头，不应作为用户可见标题
  const rawName = tr.theorem_name || '';
  const displayName = rawName.startsWith('(')
    ? (tr.theorem_ref || tr.location_hint || '')
    : rawName;
  const title = displayName
    ? `${t('ui.review.theorem')} ${index}: ${renderMathText(displayName, { inline: true })}`
    : `${t('ui.review.theorem')} ${index}`;
  const statementHtml = (tr.statement && !tr.statement.startsWith('('))
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

/** 渲染 PDF 章节审查卡片（kind=section）—— 极简审稿报告风格。 */
function renderSectionCardHtml(sec, index) {
  if (!sec) return '';
  const isZh = AppState.lang === 'zh';
  const pageLabel = sec.page_range ? ` · p.${sec.page_range}` : '';
  const titleText = `§ ${escapeHtml(sec.section_title || `Section ${index}`)}${escapeHtml(pageLabel)}`;
  const confPct = sec.confidence != null ? Math.round(sec.confidence * 100) : null;
  const confHtml = confPct != null
    ? `<span style="font-size:0.75em;font-weight:400;opacity:0.55;margin-left:8px">${isZh ? 'conf.' : 'conf.'} ${confPct}%</span>`
    : '';

  // main_claims — 只渲染 Partial 或 Incorrect
  const filteredClaims = (sec.main_claims || []).filter(c =>
    c && (c.verdict === 'Partial' || c.verdict === 'Incorrect')
  );
  const claimsHtml = filteredClaims.map(c => {
    const roleLabel = { theorem: isZh ? '定理' : 'Theorem', lemma: isZh ? '引理' : 'Lemma',
      corollary: isZh ? '推论' : 'Corollary', proposition: isZh ? '命题' : 'Prop.',
      informal_claim: isZh ? '断言' : 'Claim' }[c.role] || c.role || '';
    const verdictLabel = `(${c.verdict})`;
    const quoteHtml = c.source_quote
      ? `<blockquote class="review-quote">${renderMathText(c.source_quote)}</blockquote>` : '';
    return `
      <div class="issue-item">
        <div class="issue-content">
          <div style="font-size:12px;line-height:1.55;overflow-wrap:anywhere">
            ${roleLabel ? `<span class="issue-level info">${escapeHtml(roleLabel)}</span> ` : ''}<span style="opacity:0.6">${escapeHtml(verdictLabel)}</span>
            &nbsp;${renderMathText(c.statement || '')}
          </div>
          ${quoteHtml}
        </div>
      </div>`;
  }).join('');

  // logic_issues — [SEVERITY] 描述 / 原文引用 / 改进建议
  const logicIssHtml = (sec.logic_issues || []).map(iss => {
    const sevCls = _issueLevelCls(iss.severity);
    const quoteHtml = iss.source_quote
      ? `<blockquote class="review-quote">${renderMathText(iss.source_quote)}</blockquote>` : '';
    const fixHtml = iss.fix_suggestion
      ? `<div style="margin-top:4px;font-size:12px;color:var(--text-secondary)">→ ${renderMathText(iss.fix_suggestion)}</div>` : '';
    return `
      <div class="issue-item">
        <div class="issue-content">
          <div><span class="issue-level ${sevCls}">[${escapeHtml((iss.severity || 'info').toUpperCase())}]</span>&nbsp;${renderMathText(iss.description || '')}</div>
          ${quoteHtml}
          ${fixHtml}
        </div>
      </div>`;
  }).join('');

  // citation_issues
  const citeIssHtml = (sec.citation_issues || []).map(iss => {
    const quoteHtml = iss.source_quote
      ? `<blockquote class="review-quote">${renderMathText(iss.source_quote)}</blockquote>` : '';
    const fixHtml = iss.fix_suggestion
      ? `<div style="margin-top:4px;font-size:12px;color:var(--text-secondary)">→ ${renderMathText(iss.fix_suggestion)}</div>` : '';
    return `
      <div class="issue-item">
        <div class="issue-content">
          <div><span class="issue-level medium">[${isZh ? 'CITE' : 'CITE'}]</span>&nbsp;${renderMathText(iss.detail || iss.description || '')}</div>
          ${quoteHtml}
          ${fixHtml}
        </div>
      </div>`;
  }).join('');

  // proofs_found — 折叠
  const proofsInner = (sec.proofs_found || []).map(p => `
    <div style="margin-top:6px;font-size:12px;line-height:1.55;color:var(--text-secondary)">
      ${p.label ? `<strong>${escapeHtml(p.label)}</strong> — ` : ''}${renderMathText(p.summary || '')}
    </div>`).join('');
  const proofsHtml = proofsInner
    ? `<details style="margin-top:10px;font-size:12px"><summary style="cursor:pointer;color:var(--text-muted)">${isZh ? '▾ 证明摘要' : '▾ Proof summaries'}</summary>${proofsInner}</details>`
    : '';

  const allIssues = logicIssHtml + citeIssHtml;
  const body = claimsHtml + allIssues + proofsHtml;

  return `
    <div class="theorem-card" data-idx="${index}">
      <div class="theorem-card-header">
        <span class="theorem-card-name">${titleText}${confHtml}</span>
      </div>
      ${body ? `<div class="theorem-card-body">${body}</div>` : ''}
    </div>`;
}

function getReviewFailureKind(report) {
  if (!report || report.parse_failed !== true) return '';
  const stats = report.stats || {};
  const code = String(stats.nanonets_error_code || stats.error_code || '').toLowerCase();
  const issues = Array.isArray(report.issues) ? report.issues : [];
  const issueText = issues.map(iss => [
    iss.issue_type,
    iss.description,
    iss.message,
    iss.fix_suggestion,
  ].filter(Boolean).join(' ')).join(' ').toLowerCase();
  if (
    code === 'missing_api_key' ||
    issueText.includes('未配置') ||
    issueText.includes('api key') ||
    issueText.includes('missing_api_key')
  ) {
    return 'config';
  }
  return 'parse';
}

function renderReviewFailureSummary(el, report, kind) {
  const isZh = AppState.lang === 'zh';
  const issues = Array.isArray(report.issues) ? report.issues : [];
  const mainIssue = issues[0] || {};
  const title = kind === 'config'
    ? t('ui.review.configRequired')
    : t('ui.review.parseFailed');
  const lead = kind === 'config'
    ? t('ui.review.cannotReview')
    : t('ui.review.parseFailed');
  const suggestion = mainIssue.fix_suggestion ||
    (kind === 'config' ? t('ui.review.configHint') : t('ui.review.parseHint'));
  const description = mainIssue.description || mainIssue.message || suggestion;
  const stats = report.stats || {};
  const code = stats.nanonets_error_code || stats.error_code || '';
  const codeHtml = code
    ? renderReviewField(isZh ? '错误码' : 'Error code', String(code), { inline: true })
    : '';

  el.innerHTML = `
    <div class="review-failure ${kind === 'config' ? 'config' : 'parse'}">
      <div class="review-failure-title">
        <span class="review-failure-icon" aria-hidden="true">${kind === 'config' ? '⚙' : '!'}</span>
        <span>${escapeHtml(title)}</span>
      </div>
      <div class="review-failure-body">
        ${renderReviewField(isZh ? '状态' : 'Status', lead)}
        ${renderReviewField(isZh ? '原因' : 'Reason', description)}
        ${renderReviewField(isZh ? '处理建议' : 'Suggestion', suggestion)}
        ${codeHtml}
      </div>
    </div>`;
}

function renderReviewSummary(el, report) {
  if (!el || !report) return;
  const failureKind = getReviewFailureKind(report);
  if (failureKind) {
    renderReviewFailureSummary(el, report, failureKind);
    try { renderKatexFallback(el); } catch {}
    return;
  }
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
        ? `${t('ui.reviewComplete')}，共发现 ${topIssues.length} 个需要关注的问题；下面列出具体描述。`
        : `${t('ui.reviewComplete')}. ${topIssues.length} issue(s) need attention; concrete descriptions are listed below.`)
    : (isZh
        ? `${t('ui.reviewComplete')}，当前未发现明显问题。`
        : `${t('ui.reviewComplete')}. No obvious issues were found.`);
  // 兼容 PDF 章节审查（sections_checked）和文本审查（theorems_checked）两种路径
  const checkedCount = stats.sections_checked || stats.theorems_checked || 0;
  const checkedLabel = stats.sections_checked != null
    ? (isZh ? '个章节 ·' : 'sections ·')
    : (isZh ? '个定理 ·' : 'theorems ·');
  const pagesLabel = stats.pages_processed != null
    ? `· ${isZh ? '共' : ''}${stats.pages_processed}${isZh ? ' 页' : ' pages'}`
    : '';
  const statsHtml = `
    <div class="review-stats">
      ${isZh ? '已检验' : 'Checked'} ${checkedCount}
      ${checkedLabel}
      ${isZh ? '问题' : 'issues'} ${stats.issues_found || 0} ·
      ${isZh ? '引用核查' : 'citations'} ${stats.citations_checked || 0}
      ${pagesLabel}
      ${stats.fallback === 'single_proof'
        ? (isZh ? '· 整段证明降级' : '· single-proof fallback')
        : ''}
    </div>`;
  const globalIssuesHtml = topIssues.length
    ? `<div class="review-global-issues">${topIssues.map(iss => `
        <div class="issue-item">
          <span class="issue-level ${_issueLevelCls(iss.issue_type || iss.severity || 'info')}">${escapeHtml((iss.issue_type || iss.severity || 'INFO').toUpperCase())}</span>
          <div class="issue-content">
            ${iss.location ? renderReviewField(isZh ? '位置' : 'Location', iss.location, { inline: true }) : ''}
            ${renderReviewField(isZh ? '问题描述' : 'Issue', iss.description || iss.message || '')}
            ${iss.fix_suggestion ? renderReviewField(isZh ? '修复建议' : 'Suggestion', iss.fix_suggestion) : ''}
            ${iss.source_quote ? renderReviewField(isZh ? '原文' : 'Quote', iss.source_quote) : ''}
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
        check_citations: true,
        check_symbols: true,
        extended_thinking: false,
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
  const model = AppState.model;
  // 保存完整请求参数以支持重新生成
  _lastAttempt = {
    mode: 'formalization',
    statement,
    model
  };
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
      mode: 'aristotle',
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
  } else if (source === 'aristotle') {
    sourceHtml = `<div class="formalize-source-row">
      <span class="fbadge fbadge-mathlib">Harmonic Aristotle</span>
      <span class="formalize-source-note">${isZh ? '云端 Lean 4（Harmonic）' : 'Cloud Lean 4 (Harmonic)'}</span>
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
  const aid = compilation.aristotle_formalize_project_id;
  const pid = compilation.aristotle_prove_project_id;
  if (aid) {
    summaryParts.push(`${isZh ? '形式化任务' : 'Formalize job'}: <code style="font-size:11px">${escapeHtml(String(aid))}</code>`);
  }
  if (pid) {
    summaryParts.push(`${isZh ? '证明任务' : 'Proof job'}: <code style="font-size:11px">${escapeHtml(String(pid))}</code>`);
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
          mode: 'pipeline',
        },
        { statement }
      );
    });
  }

  renderKatexFallback(resultEl);
}

async function handleReviewing(focusText) {
  focusText = (focusText || '').trim();
  const isZh = AppState.lang === 'zh';

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

  const model = AppState.model;
  // 保存完整请求参数以支持重新生成（包括附件信息）
  _lastAttempt = {
    mode: 'reviewing',
    proofText,
    attachments: list.map(a => ({
      name: a.name,
      pageCount: a.pageCount,
      thumbnails: a.thumbnails || [],
      // 注意：rawFile不能序列化，重新生成时需要用户重新上传或使用已有的数据
    })),
    model
  };
  let userPreview;
  const pdfList = list.filter(a => a.rawFile && /\.pdf$/i.test(a.name));
  const nonPdfList = list.filter(a => !(/\.pdf$/i.test(a.name)));
  if (pdfList.length) {
    // PDF 附件用 chip 渲染，非 PDF 附件仍用纯文本
    userPreview = nonPdfList.map(a => '📎 ' + a.name).join('\n')
      + (focusText ? '\n\n' + focusText : '');
  } else if (list.length) {
    userPreview = list.map(a => '📎 ' + a.name).join('\n')
      + (focusText ? '\n\n' + focusText : '');
  } else {
    userPreview = proofText;
  }
  addMessage('user', userPreview, {
    pdfAttachments: pdfList.length ? pdfList.map(a => ({
      name: a.name,
      pageCount: a.pageCount,
      thumbnails: a.thumbnails || [],
      objectUrl: a.objectUrl || null,
    })) : undefined,
  });

  const contentEl = addMessage('ai', null);
  if (!contentEl) return;
  const initText = t('ui.preparing');
  contentEl.innerHTML = `
    <div class="review-status-pill" id="rv-status">
      <span class="spinner" aria-hidden="true"></span>
      <span class="rv-status-text">${escapeHtml(initText)}</span>
    </div>
    <div class="review-wait-tip" id="rv-wait-tip"></div>
    <div class="review-cards" id="rv-cards"></div>
    <div class="review-final" id="rv-final"></div>`;

  const waitTipEl = contentEl.querySelector('#rv-wait-tip');
  if (waitTipEl) _startReviewWaitTips(waitTipEl);

  let finalReport = null;
  const partials = [];

  try {
    await streamReview(proofText, {
      lang: AppState.lang,
      onStatus: (step, msg) => {
        const txt = contentEl.querySelector('.rv-status-text');
        if (txt) txt.textContent = msg;
        if (step === 'done') {
          contentEl.querySelector('#rv-status')?.classList.add('done');
        }
      },
      onResult: (payload) => {
        if (!payload || !payload.data) return;
        partials.push(payload.data);
        const cardsEl = contentEl.querySelector('#rv-cards');
        if (cardsEl) {
          if (payload.kind === 'section') {
            const sec = payload.data;
            const hasIssues = (sec.logic_issues && sec.logic_issues.length) ||
                              (sec.citation_issues && sec.citation_issues.length);
            if (hasIssues) {
              const html = renderSectionCardHtml(sec, payload.index || partials.length);
              cardsEl.insertAdjacentHTML('beforeend', html);
              try { renderKatexFallback(cardsEl.lastElementChild); } catch {}
              smartScroll(contentEl);
            }
          } else {
          cardsEl.insertAdjacentHTML('beforeend',
            renderTheoremCardHtml(payload.data, payload.index || partials.length));
          try { renderKatexFallback(cardsEl.lastElementChild); } catch {}
          smartScroll(contentEl);
          }
        }
      },
      onFinal: (report) => {
        finalReport = report;
      },
      onError: (e) => { throw new Error(e); },
    });

    _stopReviewWaitTips(contentEl);
    const pill = contentEl.querySelector('#rv-status');
    const txt = contentEl.querySelector('.rv-status-text');

    if (finalReport) {
      // 把流式收到的所有 theorem 卡塞回 final 报告，便于保存/重放
      const fullReport = Object.assign({}, finalReport, { theorem_reviews: partials });
      const failureKind = getReviewFailureKind(fullReport);
      if (pill) {
        pill.classList.add(failureKind ? 'error' : 'done');
      }
      if (txt) {
        txt.textContent = failureKind === 'config'
          ? t('ui.reviewConfigRequired')
          : (failureKind === 'parse' ? t('ui.reviewParseFailed') : t('ui.reviewComplete'));
      }
      renderReviewSummary(contentEl.querySelector('#rv-final'), fullReport);
      const bubble = contentEl.closest('.msg-bubble');
      if (bubble) addMessageActions(bubble, JSON.stringify(fullReport, null, 2));
    } else {
      if (pill) pill.classList.add('done');
      if (txt) txt.textContent = t('ui.reviewComplete');
    }
    // 把 AI 回复内容追加到历史
    const lastHistory = AppState.history[AppState.history.length - 1];
    if (lastHistory && lastHistory.role === 'ai' && !lastHistory.content) {
      lastHistory.content = t('ui.reviewComplete');
    }
    saveCurrentSession(isZh ? '证明审查' : 'Proof review');
    await refreshCurrentUser();
    Attachments.clear();
  } catch (err) {
    _stopReviewWaitTips(contentEl);
    if (err && err.name === 'AbortError') return;
    addErrorInline(contentEl, t('ui.err.reviewing', { e: err.message || err }));
    showToast('error', err.message || String(err));
  }
}

async function _handleReviewingPdf(attach, focusText) {
  const isZh = AppState.lang === 'zh';
  const fileName = attach.name;

  addMessage('user', focusText || '', {
    pdfAttachments: [{
      name: attach.name,
      pageCount: attach.pageCount,
      thumbnails: attach.thumbnails || [],
      objectUrl: attach.objectUrl || null,
    }],
  });

  const contentEl = addMessage('ai', null);
  if (!contentEl) return;
  contentEl.innerHTML = `
    <div class="review-status-pill" id="rv-status">
      <span class="spinner" aria-hidden="true"></span>
      <span class="rv-status-text">${escapeHtml(t('ui.reviewUploading'))}</span>
    </div>
    <div class="review-progress-wrap" id="rv-progress" style="display:none">
      <div class="review-progress-bar-bg">
        <div class="review-progress-bar" id="rv-progress-bar" style="width:0%"></div>
      </div>
      <span class="review-progress-label" id="rv-progress-label">0%</span>
    </div>
    <div class="review-wait-tip" id="rv-wait-tip"></div>
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
    else fd.append('lang', 'zh');  // 始终传 lang，默认中文
    // 关键：显式走 agent 模式，否则后端默认 pipeline，无法体验 GROBID/对齐链路。
    fd.append('mode', 'agent');
    fd.append('check_logic', String(AppState.settings.checkLogic !== false));
    fd.append('check_citations', 'true');
    fd.append('check_symbols', 'true');
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
            // 审查 pipeline 内部错误由后端以 step="error" 形式传递
            if (obj.step === 'error') {
              throw new Error(obj.status);
            }

            // 进度条：解析 "N/M" 格式（如"正在结构化审查章节 3/19：..."）
            const progressWrap = contentEl.querySelector('#rv-progress');
            const progressBar  = contentEl.querySelector('#rv-progress-bar');
            const progressLabel = contentEl.querySelector('#rv-progress-label');
            const waitTipEl    = contentEl.querySelector('#rv-wait-tip');
            const step = obj.step || '';

            if (step === 'nanonets' && progressWrap) {
              progressWrap.style.display = '';
              if (progressBar) progressBar.style.width = '8%';
              if (progressLabel) progressLabel.textContent = '8%';
              if (!_rvWaitTipTimer) _startReviewWaitTips(waitTipEl);
            } else if (step === 'nanonets_ok' && progressBar) {
              progressBar.style.width = '18%';
              if (progressLabel) progressLabel.textContent = '18%';
            } else if (step === 'section') {
              const m = /(\d+)\/(\d+)/.exec(obj.status || '');
              if (m && progressBar) {
                const n = +m[1], total = +m[2];
                const pct = Math.round(20 + (n / total) * 75);
                progressBar.style.width = pct + '%';
                if (progressLabel) progressLabel.textContent = pct + '%';
              }
            }
          } else if (obj.result) {
            const payload = obj.result;
            if (payload && payload.data) {
              partials.push(payload.data);
              const cardsEl = contentEl.querySelector('#rv-cards');
              if (cardsEl) {
                if (payload.kind === 'section') {
                  const sec = payload.data;
                  const hasIssues = (sec.logic_issues && sec.logic_issues.length) ||
                                    (sec.citation_issues && sec.citation_issues.length);
                  if (!hasIssues) { /* 无问题章节，跳过渲染 */ } else {
                    const html = renderSectionCardHtml(sec, payload.index || partials.length);
                    cardsEl.insertAdjacentHTML('beforeend', html);
                try { renderKatexFallback(cardsEl.lastElementChild); } catch {}
                smartScroll(contentEl);
                  }
                } else {
                  const html = renderTheoremCardHtml(payload.data, payload.index || partials.length);
                  cardsEl.insertAdjacentHTML('beforeend', html);
                  try { renderKatexFallback(cardsEl.lastElementChild); } catch {}
                  smartScroll(contentEl);
                }
              }
            }
          } else if (obj.final) {
            finalReport = obj.final;
          } else if (obj.error) {
            throw new Error(obj.error);
          }
        } catch (parseErr) {
          // 只吞掉 JSON.parse 产生的 SyntaxError；其他错误（如 step=error 触发的抛出）向上传
          if (!(parseErr instanceof SyntaxError)) throw parseErr;
        }
      }
    }

    const pill = contentEl.querySelector('#rv-status');
    const txt = contentEl.querySelector('.rv-status-text');
    // 进度条完成
    _stopReviewWaitTips(contentEl);
    const pb = contentEl.querySelector('#rv-progress-bar');
    const pl = contentEl.querySelector('#rv-progress-label');
    if (pb) { pb.style.width = '100%'; pb.style.transition = 'width .3s'; }
    if (pl) pl.textContent = '100%';

    if (finalReport) {
      const fullReport = Object.assign({}, finalReport, { theorem_reviews: partials });
      const failureKind = getReviewFailureKind(fullReport);
      if (pill) {
        pill.classList.add(failureKind ? 'error' : 'done');
      }
      if (txt) {
        txt.textContent = failureKind === 'config'
          ? t('ui.reviewConfigRequired')
          : (failureKind === 'parse' ? t('ui.reviewParseFailed') : t('ui.reviewComplete'));
      }
      renderReviewSummary(contentEl.querySelector('#rv-final'), fullReport);
      const bubble = contentEl.closest('.msg-bubble');
      if (bubble) addMessageActions(bubble, JSON.stringify(fullReport, null, 2));
    } else {
      // 流式中途断开：未收到 final 帧，给出警示而非"完成"
      if (pill) pill.classList.add('done');
      if (txt) txt.textContent = t('ui.reviewIncomplete');
      if (partials.length > 0) {
        // 已有部分章节结果，尝试渲染已有内容
        const partial = { overall_verdict: 'NotChecked', stats: { sections_checked: partials.length }, issues: [], theorem_reviews: partials };
        renderReviewSummary(contentEl.querySelector('#rv-final'), partial);
      }
    }
    // 与文本审查路径对齐：把 AI 回复内容追加到历史，避免回放时显示空白
    const lastHistoryPdf = AppState.history[AppState.history.length - 1];
    if (lastHistoryPdf && lastHistoryPdf.role === 'ai' && !lastHistoryPdf.content) {
      lastHistoryPdf.content = isZh ? '证明审查 (PDF) 完成' : 'PDF proof review complete';
    }
    saveCurrentSession(isZh ? '证明审查 (PDF)' : 'Proof review (PDF)');
    await refreshCurrentUser();
    Attachments.clear();
  } catch (err) {
    _stopReviewWaitTips(contentEl);
    if (err && err.name === 'AbortError') return;
    addErrorInline(contentEl, t('ui.err.reviewing', { e: err.message || err }));
    showToast('error', err.message || String(err));
  } finally {
    AppState.set('isStreaming', false);
  }
}

async function handleSearching(query) {
  const model = AppState.model;
  // 保存完整请求参数以支持重新生成
  _lastAttempt = {
    mode: 'searching',
    statement: query,
    model
  };
  addMessage('user', query);
  const contentEl = addMessage('ai', null);
  if (contentEl) contentEl.innerHTML = makeThinkingInnerHtml(t('ui.searchingTheorems'));

  AppState.set('isStreaming', true);
  const ctrl = new AbortController();
  AppState._abortController = ctrl;

  try {
    const resp = await fetch(`${API_BASE}/search?${new URLSearchParams({ q: query, top_k: 10 })}`, { signal: ctrl.signal });
    if (!resp.ok) {
      let detail = `HTTP ${resp.status}`;
      try { const e = await resp.json(); detail = e.detail || e.error?.message || detail; } catch {}
      throw new Error(detail);
    }
    const data = await resp.json();
    renderSearchResults(contentEl, data);
    const bubbleEl = contentEl?.closest('.msg-bubble');
    if (bubbleEl) addMessageActions(bubbleEl, query);
    // 把 AI 回复内容追加到历史
    const lastHistory = AppState.history[AppState.history.length - 1];
    if (lastHistory && lastHistory.role === 'ai' && !lastHistory.content) {
      lastHistory.content = `定理检索：${query}`;
    }
    saveCurrentSession(query);
    await refreshCurrentUser();
  } catch (err) {
    if (err && err.name === 'AbortError') return;
    addErrorInline(contentEl, t('ui.err.searching', { e: err.message || err }));
    showToast('error', err.message || String(err));
  } finally {
    AppState.set('isStreaming', false);
  }
}

function renderSearchResults(contentEl, data) {
  if (!data || !data.results) {
    contentEl.innerHTML = `<div class="search-empty">${t('ui.search.noResult')}</div>`;
    return;
  }
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
    // 只允许 http/https 协议，防止 javascript: 等恶意链接
    const safeLink = /^https?:\/\//i.test(link) ? link : '';
    const authors = Array.isArray(r.paper_authors) && r.paper_authors.length
      ? r.paper_authors.slice(0, 3).join(', ') + (r.paper_authors.length > 3 ? ' et al.' : '')
      : '';

    const nameHtml = safeLink
      ? `<a class="search-result-name-link" href="${escapeHtml(safeLink)}" target="_blank" rel="noopener">${renderInlineMd(name)}</a>`
      : `<span>${renderInlineMd(name)}</span>`;

    const sourceHtml = (paper || safeLink) ? `
      <div class="search-result-source">
        <span class="search-result-source-icon">↗</span>
        <span class="search-result-source-body">
          ${paper ? `<span class="search-result-paper">${renderInlineMd(paper)}</span>` : ''}
          ${authors ? `<span class="search-result-authors">${escapeHtml(authors)}</span>` : ''}
          ${safeLink ? `<a class="search-result-link" href="${escapeHtml(safeLink)}" target="_blank" rel="noopener">${escapeHtml(safeLink.replace(/^https?:\/\//, '').split('/').slice(0, 3).join('/'))}</a>` : ''}
        </span>
      </div>` : '';

    return `
      <div class="search-result-item">
        <div class="search-result-header">
          <div class="search-result-name">${nameHtml}</div>
          <div class="search-result-score ${simCls}">${simPct}%</div>
        </div>
        ${slogan ? `<div class="search-result-slogan">${renderMathText(slogan)}</div>` : ''}
        ${decl ? `<div class="search-result-decl lean-decl">${renderMathText(decl)}</div>` : ''}
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
  // 原子性并发控制：防止重复提交
  if (AppState.isStreaming || _sendLock) return;
  _sendLock = true;

  try {
    const textarea = document.getElementById('input-textarea');
    const text = textarea?.value?.trim();
    const savedText = text;  // 备份输入以便失败时恢复

    if (!text && AppState.mode !== 'reviewing') {
      const row = textarea?.closest('.textarea-row');
      row?.classList.add('shake');
      setTimeout(() => row?.classList.remove('shake'), 500);
      // 添加toast提示
      const isZh = AppState.lang === 'zh';
      showToast('warning', isZh ? '请输入内容后再发送' : 'Please enter something before sending');
      return;
    }

    // 前端输入长度预检（与后端 10000 字符上限一致），避免无谓 422 往返
    const _MODE_CHAR_LIMIT = 10000;
    if (text && text.length > _MODE_CHAR_LIMIT && AppState.mode !== 'reviewing') {
      const isZh = AppState.lang === 'zh';
      showToast('warning', isZh
        ? `输入内容超过 ${_MODE_CHAR_LIMIT.toLocaleString()} 字符限制，请精简后再发送`
        : `Input exceeds ${_MODE_CHAR_LIMIT.toLocaleString()} character limit`);
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

    try {
      switch (AppState.mode) {
        case 'learning':      await handleLearning(text);      break;
        case 'solving':       await handleSolving(text);       break;
        case 'reviewing':     await handleReviewing(text);     break;
        case 'searching':     await handleSearching(text);     break;
        case 'formalization': await handleFormalization(text); break;
      }
    } catch (err) {
      // 失败时恢复输入内容
      if (savedText && !textarea.value) {
        textarea.value = savedText;
        const autoResize = (el) => {
          if (!el) return;
          el.style.height = 'auto';
          el.style.height = Math.min(el.scrollHeight, 400) + 'px';
        };
        autoResize(textarea);
      }
      throw err;
    }
  } finally {
    // 确保锁始终释放（即使发生异常）
    _sendLock = false;
    _isRegenerating = false;  // 重置重新生成标志
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
    try {
      const serialized = JSON.stringify(data);
      const sizeKB = new Blob([serialized]).size / 1024;

      // 单项大小检查：超过 2MB 自动清理
      if (sizeKB > 2048) {
        console.warn(`[ProjectMemory] Project ${pid} data too large: ${sizeKB.toFixed(2)} KB`);

        // 自动清理：仅保留最近 10 个 session
        if (data.sessions && data.sessions.length > 10) {
          data.sessions = data.sessions.slice(0, 10);
          return this.save(pid, data);  // 重试保存
        }
      }

      localStorage.setItem(this._key(pid), serialized);

    } catch (err) {
      console.error(`[ProjectMemory] Failed to save ${pid}:`, err);

      if (err.name === 'QuotaExceededError') {
        // 存储已满：尝试降级保存核心数据
        try {
          const coreData = {
            concepts: data.concepts || [],
            open_questions: data.open_questions || [],
            sessions: (data.sessions || []).slice(0, 5)  // 仅保留最近 5 个
          };
          localStorage.setItem(this._key(pid), JSON.stringify(coreData));
          showToast('warning', 'Storage full, saved core data only');
        } catch {
          showToast('error', 'Cannot save data - storage full');
        }
      }
    }
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
  const modeMap = { learning: 'L', solving: 'S', reviewing: 'R', searching: 'T', formalization: 'F' };
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
  if (checkHealth._running) return;  // 防止并发重叠请求
  checkHealth._running = true;
  const dot = document.getElementById('health-dot');
  const setStatus = (id, status) => {
    const el = document.getElementById(id);
    if (!el) return;
    const isOk = status === 'ok';
    el.textContent = status;
    el.className = `status-badge ${isOk ? 'ok' : status === '--' ? 'unknown' : 'unavailable'}`;
  };

  // 12 秒超时：避免 fetch 无限挂起导致 _running 永不清除
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 12000);

  try {
    const resp = await fetch(`${API_BASE}/health`, { signal: ctrl.signal });
    clearTimeout(timer);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    const llmStatus = data.dependencies?.llm?.status || '--';
    setStatus('status-llm', llmStatus === 'ok' ? 'ok' : llmStatus);
    const nanConfigured = data.dependencies?.nanonets?.api_key_configured || AppState.config?.nanonets?.api_key_configured;
    const nanStatus = data.dependencies?.nanonets?.status
      || data.dependencies?.paper_review_agent?.nanonets?.status
      || (nanConfigured ? 'ok' : '--');
    setStatus('status-nanonets', nanStatus === 'ok' ? 'ok' : nanStatus);
    if (dot) { dot.textContent = '●'; dot.className = 'health-dot online'; }

    const llmInfo = data.llm || {};
    if (!AppState.config && (llmInfo.base_url || llmInfo.model)) {
      applyConfigToUi({ llm: llmInfo, config_path: '' });
    }
  } catch (err) {
    clearTimeout(timer);
    const isTimeout = err && err.name === 'AbortError';
    setStatus('status-llm', isTimeout ? 'timeout' : 'offline');
    setStatus('status-nanonets', '--');
    if (dot) { dot.textContent = '●'; dot.className = 'health-dot offline'; }
  } finally {
    checkHealth._running = false;
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

  // 打开面板时自动检查服务状态
  if (_panelOpen) {
    checkHealth();
  }
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
  let authMode = 'login';
  const syncAuthTabs = () => {
    document.getElementById('auth-tab-login')?.classList.toggle('active', authMode === 'login');
    document.getElementById('auth-tab-register')?.classList.toggle('active', authMode === 'register');
    const submit = document.getElementById('auth-submit');
    if (submit) submit.textContent = authMode === 'login' ? '登录' : '注册';
    const pwd = document.getElementById('auth-password');
    if (pwd) pwd.setAttribute('autocomplete', authMode === 'login' ? 'current-password' : 'new-password');
  };
  document.getElementById('auth-tab-login')?.addEventListener('click', () => { authMode = 'login'; syncAuthTabs(); });
  document.getElementById('auth-tab-register')?.addEventListener('click', () => { authMode = 'register'; syncAuthTabs(); });
  document.getElementById('auth-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const errEl = document.getElementById('auth-error');
    const submit = document.getElementById('auth-submit');
    const username = document.getElementById('auth-username')?.value.trim() || '';
    const password = document.getElementById('auth-password')?.value || '';
    try {
      if (errEl) errEl.textContent = '';
      if (submit) submit.disabled = true;
      const data = await apiPost(authMode === 'login' ? '/auth/login' : '/auth/register', { username, password });
      AppState.user = data.user;
      AppState.userId = data.user?.id || '';
      showAppShell();
      await finishAppInitAfterAuth();
    } catch (err) {
      if (errEl) errEl.textContent = err.message || String(err);
    } finally {
      if (submit) submit.disabled = false;
    }
  });
  syncAuthTabs();

  // 卡片点击
  document.querySelectorAll('.feature-card').forEach(card => {
    const activate = () => {
      const mode = card.dataset.mode;
      const action = card.dataset.action;
      if (mode === 'formalization') {
        window.open('https://aristotle.harmonic.fun/dashboard', '_blank', 'noopener');
        return;
      }
      if (mode) {
        switchMode(mode, { force: true });
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

  // 顶部 mode tabs 仅作为视觉指示器，不可点击切换（用户需通过主界面切换模式）
  // document.querySelectorAll('.mode-tab').forEach(tab => {
  //   tab.addEventListener('click', () => {
  //     const mode = tab.dataset.mode;
  //     switchMode(mode);
  //   });
  // });

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
  document.getElementById('btn-logout')?.addEventListener('click', async () => {
    await fetch(`${API_BASE}/auth/logout`, { method: 'POST' }).catch(() => {});
    location.reload();
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
  document.getElementById('send-btn')?.addEventListener('click', () => {
    if (AppState.isStreaming) {
      stopActiveRun({ markStream: true });
    } else {
      sendMessage();
    }
  });
  document.getElementById('input-textarea')?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    if (e.key === 'Escape' && AppState.isStreaming) {
      stopActiveRun({ markStream: true });
    }
  });
  document.getElementById('input-textarea')?.addEventListener('input', e => autoResize(e.target));

  document.getElementById('stop-btn')?.addEventListener('click', () => {
    stopActiveRun({ markStream: true });
  });

  initChip('mode-chip', 'mode-dropdown', (value) => switchMode(value));
  initChip('model-chip', 'model-dropdown', (value, label) => {
    const shortName = label.split('\n').map(s => s.trim()).filter(Boolean).join(' ');
    setActiveModel(value, shortName);
  });

  // 模型信息卡片（Cursor 风格：hover 显示模型介绍）
  _initModelInfoCard();

  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', () => applyLang(btn.dataset.lang));
  });

  document.getElementById('input-max-theorems')?.addEventListener('change', e => { AppState.settings.maxTheorems = parseInt(e.target.value) || 5; });
  const waitTipsToggle = document.getElementById('toggle-wait-tips');
  if (waitTipsToggle) {
    waitTipsToggle.checked = !!AppState.settings.waitTips;
    waitTipsToggle.addEventListener('change', e => {
      AppState.settings.waitTips = !!e.target.checked;
      localStorage.setItem('vp_wait_tips', AppState.settings.waitTips ? '1' : '0');
      apiPost('/config/ui', { wait_tips: AppState.settings.waitTips }).catch(() => {});
      if (!AppState.settings.waitTips) {
        stopWaitTips();
        _stopReviewWaitTips(null);
        document.querySelectorAll('#rv-wait-tip').forEach(el => { el.textContent = ''; });
      }
    });
  }
  // 审查选项
  document.getElementById('toggle-check-logic')?.addEventListener('change', e => { AppState.settings.checkLogic = e.target.checked; });
  document.querySelectorAll('input[name=level]').forEach(r => {
    r.addEventListener('change', e => { AppState.settings.level = e.target.value; });
  });

  // ── LLM preset 快速填入 ──────────────────────────────────────
  const LLM_PRESETS = {
    deepseek: {
      base_url: 'https://api.deepseek.com/v1',
      model: 'deepseek-v4-pro',
    },
    gemini: {
      base_url: 'https://generativelanguage.googleapis.com/v1beta/openai/',
      model: 'gemini-3.1-pro-preview',
    },
  };
  document.querySelectorAll('.llm-preset-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const p = LLM_PRESETS[btn.dataset.preset];
      if (!p) return;
      const baseEl = document.getElementById('input-llm-base-url');
      const modelEl = document.getElementById('input-llm-model');
      if (baseEl) baseEl.value = p.base_url;
      if (modelEl) modelEl.value = p.model;
      updateConfigState({ api_key_configured: false }, AppState.config?.config_path || '');
      document.getElementById('input-llm-api-key')?.focus();
    });
  });

  // ── LLM 配置保存 ─────────────────────────────────────────────
  document.getElementById('btn-save-llm')?.addEventListener('click', async () => {
    const btn = document.getElementById('btn-save-llm');
    const payload = {
      base_url: document.getElementById('input-llm-base-url')?.value.trim() || '',
      api_key:  document.getElementById('input-llm-api-key')?.value.trim() || '',
      model:    document.getElementById('input-llm-model')?.value.trim() || '',
    };
    try {
      if (btn) { btn.disabled = true; btn.textContent = t('panel.saving'); }
      await apiPost('/config/llm', payload);

      if (payload.model) {
        setActiveModel(payload.model);
      }

      if (btn) { btn.textContent = t('panel.saved'); }
      await loadAppConfig();
      const keyEl = document.getElementById('input-llm-api-key');
      if (keyEl) keyEl.value = '';
      setTimeout(() => { if (btn) { btn.disabled = false; btn.textContent = t('panel.saveLlm'); } }, 2000);
      checkHealth();
    } catch (err) {
      if (btn) { btn.disabled = false; btn.textContent = t('panel.saveFailed'); }
      showToast('error', t('panel.saveFailedHint'));
      console.error('LLM config save failed', err);
    }
  });

  // ── Nanonets 配置保存 ─────────────────────────────────────────
  document.getElementById('btn-save-nanonets')?.addEventListener('click', async () => {
    const btn = document.getElementById('btn-save-nanonets');
    const api_key = document.getElementById('input-nanonets-key')?.value.trim() || '';
    try {
      if (btn) { btn.disabled = true; btn.textContent = t('panel.saving'); }
      await apiPost('/config/nanonets', { api_key });
      if (btn) { btn.textContent = t('panel.saved'); }
      await loadAppConfig();
      const keyEl = document.getElementById('input-nanonets-key');
      if (keyEl) keyEl.value = '';
      setTimeout(() => { if (btn) { btn.disabled = false; btn.textContent = t('panel.saveNanonets'); } }, 2000);
    } catch (err) {
      if (btn) { btn.disabled = false; btn.textContent = t('panel.saveFailed'); }
      showToast('error', t('panel.saveFailedHint'));
      console.error('Nanonets config save failed', err);
    }
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
    const _MAX_PDF_SIZE  = 50 * 1024 * 1024;  // 50 MB for PDFs (matches server limit)
    for (const file of files) {
      if (!allowExt.test(file.name)) {
        showToast('error', t('ui.err.unsupportedFile'));
        continue;
      }
      const isPdf = /\.pdf$/i.test(file.name);
      if (isPdf) {
        if (file.size > _MAX_PDF_SIZE) {
          showToast('error', AppState.lang === 'zh' ? 'PDF 超过 50 MB 上限' : 'PDF exceeds 50 MB limit');
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
      switchMode(modes[parseInt(e.key) - 1]);
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

async function finishAppInitAfterAuth() {
  showAppShell();
  AppState.view = 'home';
  const homeEl = document.getElementById('home-view');
  const chatEl = document.getElementById('chat-view');
  if (homeEl) homeEl.style.display = 'flex';
  if (chatEl) chatEl.style.display = 'none';
  updateUserUi();
  UI.switchView(AppState.view);
  UI.updateMode(AppState.mode);
  _syncModeTabs();
  localStorage.removeItem('vp_custom_model');
  Promise.resolve()
    .then(loadAppConfig)
    .then(() => SessionHistory.sync())
    .catch(err => console.warn('Post-login init failed', err));
  setTimeout(checkHealth, 1200);
}

/* ─────────────────────────────────────────────────────────────
   22. 初始化
───────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  let didBind = false;
  const doInit = async () => {
    applyTheme(detectTheme());
    try {
      initRenderer();
    } catch (err) {
      console.warn('Renderer initialization failed; continuing with plain text fallback.', err);
    }
    applyLang(detectLang());
    _syncLangTopbar();
    if (!didBind) {
      bindEvents();
      didBind = true;
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
        if (!localStorage.getItem('vp_theme')) applyTheme(e.matches ? 'dark' : 'light');
      });
    }
    try {
      const data = await authMe();
      AppState.user = data.user;
      AppState.userId = data.user?.id || '';
      applyApiConfigVisibility(data.auth?.can_configure_api !== false);
      await finishAppInitAfterAuth();
    } catch {
      showAuth();
    }
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
