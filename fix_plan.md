# Bug 修复计划

## 问题汇总

### 1. 顶部模式切换栏可点击问题
**现状**: app.js:6008-6013 行为所有 `.mode-tab` 绑定了点击事件
**要求**: 顶部栏仅作为视觉指示器，不可点击，用户只能通过返回主界面来切换模式
**修复**: 移除事件监听器，可选添加CSS禁用pointer-events

### 2. 重新生成按钮逻辑不完善
**现状**: `_lastAttempt` 只保存 `{mode, statement, proofText}`
**问题**: 
- learning模式：未保存level参数
- reviewing模式：未保存attachments附件信息
- 所有模式：未保存model、lang等全局参数

**修复**: 
1. 修改各handle函数，将完整请求参数保存到_lastAttempt
2. 修改regenerateMessage，根据模式恢复完整上下文

### 3. LaTeX 渲染残留
**现状**: 后端已通过text_sanitize模块处理
**检查点**: 
- 论文审查的PDF工作流输出
- 论文审查的文本工作流输出
- 其他模式的输出
**验证**: 端到端测试确保无LaTeX控制序列残留

## 修复步骤

1. ✅ 定位问题根源
2. 修改前端代码
3. 设计测试用例
4. 端到端验证
5. 提交代码
