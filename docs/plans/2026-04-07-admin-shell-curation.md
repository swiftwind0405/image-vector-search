# Admin Shell Curation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将现有管理端重设计为深色策展工作台，在不改后端接口与核心交互能力的前提下，统一全局壳层、页面结构和视觉语言。

**Architecture:** 先修改全局主题令牌与共享壳层，建立新的深色策展基座；再逐步重构 `Dashboard`、`Search`、`Login` 三个关键页面；最后将 `Images`、`Tags`、`Categories` 融入统一布局体系，并用现有测试加少量新增测试做回归保护。

**Tech Stack:** React 18, TypeScript, React Router, TanStack Query, Tailwind CSS, shadcn/ui, Vitest, Testing Library

---

### Task 1: 为全局壳层重设计补测试约束

**Files:**
- Modify: `src/image_vector_search/frontend/src/test/admin-navigation.test.tsx`
- Test: `src/image_vector_search/frontend/src/test/admin-navigation.test.tsx`

**Step 1: Write the failing test**

补充或调整测试，断言：

- 导航中仍可见 `Image Search`
- 关键路由 `Dashboard`、`Search`、`Tags`、`Categories`、`Images` 仍可导航
- 主内容区存在统一页级标题或上下文结构

**Step 2: Run test to verify it fails**

Run: `npm test -- src/test/admin-navigation.test.tsx`
Expected: FAIL，因为当前壳层还没有新的上下文结构与标题组织。

**Step 3: Write minimal implementation**

先不动页面细节，只在共享壳层中加入新的语义结构占位，保证测试有明确目标。

涉及文件：

- `src/image_vector_search/frontend/src/components/Layout.tsx`

**Step 4: Run test to verify it passes**

Run: `npm test -- src/test/admin-navigation.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add src/image_vector_search/frontend/src/test/admin-navigation.test.tsx src/image_vector_search/frontend/src/components/Layout.tsx
git commit -m "test: lock admin shell navigation structure"
```

### Task 2: 重建全局主题令牌与基础背景层次

**Files:**
- Modify: `src/image_vector_search/frontend/src/index.css`
- Modify: `src/image_vector_search/frontend/tailwind.config.ts`
- Test: `src/image_vector_search/frontend/src/test/admin-navigation.test.tsx`

**Step 1: Write the failing test**

如果现有测试没有覆盖主题钩子，补一个轻量断言，验证应用根节点或主体存在新的主题类名或布局钩子，例如深色背景层或新的 shell class。

**Step 2: Run test to verify it fails**

Run: `npm test -- src/test/admin-navigation.test.tsx`
Expected: FAIL，因为新的主题令牌和壳层 class 还不存在。

**Step 3: Write minimal implementation**

修改：

- `src/image_vector_search/frontend/src/index.css`
- `src/image_vector_search/frontend/tailwind.config.ts`

实现：

- 将默认颜色令牌切为深色策展体系
- 增加更适合策展后台的背景层、强调色、阴影和文本对比
- 保留现有 shadcn 变量兼容性，避免基础控件失效

**Step 4: Run test to verify it passes**

Run: `npm test -- src/test/admin-navigation.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add src/image_vector_search/frontend/src/index.css src/image_vector_search/frontend/tailwind.config.ts src/image_vector_search/frontend/src/test/admin-navigation.test.tsx
git commit -m "feat: add curated dark theme tokens"
```

### Task 3: 重做共享壳层布局与导航视觉

**Files:**
- Modify: `src/image_vector_search/frontend/src/components/Layout.tsx`
- Possibly Modify: `src/image_vector_search/frontend/src/lib/utils.ts`
- Test: `src/image_vector_search/frontend/src/test/admin-navigation.test.tsx`

**Step 1: Write the failing test**

补充测试断言：

- 侧边导航在桌面端仍可访问
- 主区域包含统一顶部上下文栏容器
- 当前路由高亮语义仍然存在

**Step 2: Run test to verify it fails**

Run: `npm test -- src/test/admin-navigation.test.tsx`
Expected: FAIL，因为当前 `Layout` 仍是简单的侧栏加 `Outlet`。

**Step 3: Write minimal implementation**

修改 `src/image_vector_search/frontend/src/components/Layout.tsx`：

- 重排侧边栏为策展式目录导航
- 增加顶部上下文栏框架
- 调整主内容区宽度、滚动与背景层次
- 保留登出流程和现有路由行为

**Step 4: Run test to verify it passes**

Run: `npm test -- src/test/admin-navigation.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add src/image_vector_search/frontend/src/components/Layout.tsx src/image_vector_search/frontend/src/test/admin-navigation.test.tsx src/image_vector_search/frontend/src/lib/utils.ts
git commit -m "feat: redesign admin shell layout"
```

### Task 4: 重做 Dashboard 为图库总览台

**Files:**
- Modify: `src/image_vector_search/frontend/src/pages/DashboardPage.tsx`
- Create or Modify: `src/image_vector_search/frontend/src/components/StatusHero.tsx`
- Test: `src/image_vector_search/frontend/src/test/admin-navigation.test.tsx`

**Step 1: Write the failing test**

新增或调整测试，验证：

- 页面仍显示核心索引信息
- 主动作 `Incremental Update` 与 `Full Rebuild` 可见
- 最近任务区域仍保留
- 页面包含新的总览标题或总览描述

**Step 2: Run test to verify it fails**

Run: `npm test -- src/test/admin-navigation.test.tsx`
Expected: FAIL，因为当前页面仍是标准卡片结构。

**Step 3: Write minimal implementation**

修改 `src/image_vector_search/frontend/src/pages/DashboardPage.tsx`，必要时新增展示组件：

- 将覆盖率与总量做成主视觉统计区
- 将近期任务重排为更轻的时间流或状态区
- 将模型信息、向量数量等压缩为辅助信息带

**Step 4: Run test to verify it passes**

Run: `npm test -- src/test/admin-navigation.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add src/image_vector_search/frontend/src/pages/DashboardPage.tsx src/image_vector_search/frontend/src/components/StatusHero.tsx src/image_vector_search/frontend/src/test/admin-navigation.test.tsx
git commit -m "feat: redesign dashboard overview"
```

### Task 5: 重做 Search 为策展式检索舞台

**Files:**
- Modify: `src/image_vector_search/frontend/src/pages/SearchPage.tsx`
- Modify: `src/image_vector_search/frontend/src/components/SearchResultCard.tsx`
- Modify: `src/image_vector_search/frontend/src/components/ImageModal.tsx`
- Test: `src/image_vector_search/frontend/src/test/filter.test.ts`

**Step 1: Write the failing test**

调整或新增测试，覆盖：

- 文本检索输入仍可提交
- 相似图检索输入仍可提交
- 结果区域在有数据时渲染
- 结果计数或查询上下文可见

**Step 2: Run test to verify it fails**

Run: `npm test -- src/test/filter.test.ts`
Expected: FAIL，因为页面结构将从双卡片改成统一检索舞台，原断言会失效或缺失。

**Step 3: Write minimal implementation**

修改：

- `src/image_vector_search/frontend/src/pages/SearchPage.tsx`
- `src/image_vector_search/frontend/src/components/SearchResultCard.tsx`
- `src/image_vector_search/frontend/src/components/ImageModal.tsx`

实现：

- 合并检索入口为统一顶部区域
- 放大结果区，降低卡片感
- 优化结果项层级与灯箱式查看体验

**Step 4: Run test to verify it passes**

Run: `npm test -- src/test/filter.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add src/image_vector_search/frontend/src/pages/SearchPage.tsx src/image_vector_search/frontend/src/components/SearchResultCard.tsx src/image_vector_search/frontend/src/components/ImageModal.tsx src/image_vector_search/frontend/src/test/filter.test.ts
git commit -m "feat: redesign search workspace"
```

### Task 6: 统一 Images 浏览器的策展布局

**Files:**
- Modify: `src/image_vector_search/frontend/src/components/ImageBrowser.tsx`
- Modify: `src/image_vector_search/frontend/src/components/GalleryGrid.tsx`
- Modify: `src/image_vector_search/frontend/src/components/GalleryCard.tsx`
- Modify: `src/image_vector_search/frontend/src/components/FilterBar.tsx`
- Test: `src/image_vector_search/frontend/src/test/FilterBar.test.tsx`

**Step 1: Write the failing test**

新增或调整测试，验证：

- 标题仍显示
- 过滤栏与视图切换仍然可用
- 图片列表/网格仍然渲染
- 批量或选择相关控件未丢失

**Step 2: Run test to verify it fails**

Run: `npm test -- src/test/FilterBar.test.tsx`
Expected: FAIL，因为图片浏览器布局和交互壳层将发生变化。

**Step 3: Write minimal implementation**

修改：

- `src/image_vector_search/frontend/src/components/ImageBrowser.tsx`
- `src/image_vector_search/frontend/src/components/GalleryGrid.tsx`
- `src/image_vector_search/frontend/src/components/GalleryCard.tsx`
- `src/image_vector_search/frontend/src/components/FilterBar.tsx`

实现：

- 将图片浏览区做成更开放的画布
- 将过滤、视图切换、批量操作整合为统一工具条
- 降低边框和卡片感，让图片本身承担主要信息

**Step 4: Run test to verify it passes**

Run: `npm test -- src/test/FilterBar.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add src/image_vector_search/frontend/src/components/ImageBrowser.tsx src/image_vector_search/frontend/src/components/GalleryGrid.tsx src/image_vector_search/frontend/src/components/GalleryCard.tsx src/image_vector_search/frontend/src/components/FilterBar.tsx src/image_vector_search/frontend/src/test/FilterBar.test.tsx
git commit -m "feat: redesign image browsing surfaces"
```

### Task 7: 重排 Tags 与 Categories 页面结构

**Files:**
- Modify: `src/image_vector_search/frontend/src/pages/TagsPage.tsx`
- Modify: `src/image_vector_search/frontend/src/pages/CategoriesPage.tsx`
- Modify: `src/image_vector_search/frontend/src/components/CategoryTree.tsx`
- Test: `src/image_vector_search/frontend/src/test/categories.test.ts`

**Step 1: Write the failing test**

补充测试，验证：

- 标签创建入口仍可用
- 分类创建入口仍可用
- 跳转到标签图片页与分类图片页的入口仍存在
- 批量选择相关文本或控件仍可见

**Step 2: Run test to verify it fails**

Run: `npm test -- src/test/categories.test.ts`
Expected: FAIL，因为页面将从卡片式管理页改为更轻的编排布局。

**Step 3: Write minimal implementation**

修改：

- `src/image_vector_search/frontend/src/pages/TagsPage.tsx`
- `src/image_vector_search/frontend/src/pages/CategoriesPage.tsx`
- `src/image_vector_search/frontend/src/components/CategoryTree.tsx`

实现：

- 将创建区、列表区、批量区重组成统一的轻量编排页
- 保留现有 CRUD 与批量删除逻辑
- 提升层级扫读性，减少大块卡片容器

**Step 4: Run test to verify it passes**

Run: `npm test -- src/test/categories.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add src/image_vector_search/frontend/src/pages/TagsPage.tsx src/image_vector_search/frontend/src/pages/CategoriesPage.tsx src/image_vector_search/frontend/src/components/CategoryTree.tsx src/image_vector_search/frontend/src/test/categories.test.ts
git commit -m "feat: redesign taxonomy management pages"
```

### Task 8: 重做登录页首屏体验

**Files:**
- Modify: `src/image_vector_search/frontend/src/pages/LoginPage.tsx`
- Test: `src/image_vector_search/frontend/src/test/auth-flow.test.tsx`

**Step 1: Write the failing test**

调整测试，确保：

- 用户名、密码输入仍存在
- 提交按钮仍可触发登录
- 错误文案仍会显示
- 页面显示新的产品标题或后台说明

**Step 2: Run test to verify it fails**

Run: `npm test -- src/test/auth-flow.test.tsx`
Expected: FAIL，因为登录页结构将从单卡片变成完整首屏。

**Step 3: Write minimal implementation**

修改 `src/image_vector_search/frontend/src/pages/LoginPage.tsx`：

- 重做为完整首屏布局
- 建立左侧氛围区与右侧表单区
- 保留现有登录逻辑和错误处理

**Step 4: Run test to verify it passes**

Run: `npm test -- src/test/auth-flow.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add src/image_vector_search/frontend/src/pages/LoginPage.tsx src/image_vector_search/frontend/src/test/auth-flow.test.tsx
git commit -m "feat: redesign login entry page"
```

### Task 9: 运行前端聚焦验证

**Files:**
- No code changes required unless failures are found

**Step 1: Run targeted frontend tests**

Run: `npm test -- src/test/admin-navigation.test.tsx src/test/auth-flow.test.tsx src/test/categories.test.ts src/test/filter.test.ts src/test/FilterBar.test.tsx src/test/images-api.test.ts`
Expected: PASS

**Step 2: Run frontend build**

Run: `npm run build`
Expected: PASS，TypeScript 与 Vite 构建通过。

**Step 3: Fix any regressions**

若测试或构建失败，按失败信息做最小修复，再重复执行相关命令直到通过。

**Step 4: Commit final adjustments if needed**

```bash
git add <any changed files>
git commit -m "test: verify curated admin shell redesign"
```
