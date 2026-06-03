# 🤖 GitHub 中文区 AI 热门项目

GitHub Trending 中文区 AI 项目排行榜，每周/每月更新。

## 项目结构

```
github-ai-trending/
├── index.html      # 主页面（含 CSS 和 JS）
├── vercel.json     # Vercel 部署配置
├── package.json    # 项目元信息
├── .gitignore
└── README.md
```

## 本地预览

```bash
npx serve .
```

## 部署到 Vercel

### 方式一：Vercel CLI

```bash
npm i -g vercel
vercel --prod
```

### 方式二：Vercel Dashboard

1. 将本目录推送到 GitHub 仓库
2. 访问 [vercel.com/new](https://vercel.com/new)
3. 导入该仓库
4. 保持默认设置（Framework Preset: `Other`），点击 Deploy

## 数据更新

项目数据来自 GitHub Trending，手动更新 `index.html` 中的项目列表和更新时间即可。
