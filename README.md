# Codevember 2026 社区作品档案

以 [@thespite 的 30 条提示词](https://x.com/thespite/status/2116974998212772095)
为每日主题索引，收录可公开核实的 2026 年创意编程作品。作者有自己的提示词时，按作者给出的主题收录。
包含作品链接、作者、来源和可获取的主图。只有发布帖的作品会直接链接到发布帖。
本项目包含独立的网页、采集器和主题列表，作品卡片链接到创作者公开的作品页或发布帖。

## 本地预览

在本项目目录运行以下命令，然后访问 [本地作品档案](http://127.0.0.1:8026/)。

```sh
python3 -m http.server 8026 --bind 127.0.0.1
```

## 更新数据

```sh
python3 -m pip install -r requirements.txt
python3 collect.py --check-images
```

采集脚本读取受跟踪的作者画廊、公开仓库和部分公开社交动态。脚本将结果写入
`data/catalogue.json`，按作者、主题和作品链接合并，保留已有记录。
运行时若有来源无法读取，脚本会输出相应来源并继续处理其余数据。
网页刷新后会读取更新后的档案。

遇到新作者、只发布在社交平台上的作品或独立托管作品，可在核对作者和作品来源后追加到
`entries.json`。作品记录使用 `creator`、`title`、`url`、`source`、
可选的 `image`（原图 URL 或 `./covers/` 下的本地截图），以及 `day`（1–30）或 `theme`（作者自选主题）。新作者记录使用
`creators` 字典，包含 `name`、可选的 `handle` 和 `url`。能取得发布帖主图时链接原图。
作品链接和署名以作者公开的信息为准。

## 线上展示与同步

线上站点为 [coolcode.liuwa.xyz](https://coolcode.liuwa.xyz/)。Vercel 从 GitHub 的 `main` 分支构建静态站点。
每天 22:00（北京时间）在本机运行采集。数据先写入本地并校验，有变化时再提交并推送到 GitHub。

运行 `node scripts/build.mjs` 可在本机生成 `dist/`。构建产物包含网页、作品索引和本地封面。
