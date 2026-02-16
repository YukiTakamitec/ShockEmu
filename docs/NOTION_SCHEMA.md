# Notion Schema

## 方針
- Notion は業務メタ情報の SoT。
- 実体本文は GitHub 正本へのリンクで運用する。

## Database: Projects
- `Project Name` (title, required)
- `Project ID` (rich_text, unique)
- `Status` (select: Planned/In Progress/Blocked/Done)
- `Priority` (select: P0/P1/P2/P3)
- `Owner` (person, required)
- `Due` (date)
- `Decision Log` (rich_text)
- `GitHub Repo` (url)
- `Related Tasks` (relation -> Tasks)
- `Related Knowledge` (relation -> Knowledge)
- `Last Sync` (date)

## Database: Tasks
- `Task Name` (title, required)
- `Task ID` (rich_text, unique)
- `Project` (relation -> Projects, required)
- `Status` (select: Backlog/Todo/Doing/Review/Done/Blocked)
- `Execution State` (select: Not Started/Issue Open/PR Open/CI Failed/Merged)
- `Priority` (select: P0/P1/P2/P3, Notion only)
- `Due` (date, Notion only)
- `Owner` (person, Notion only)
- `GitHub Issue Link` (url)
- `GitHub PR Link` (url)
- `Summary` (rich_text)
- `Last Sync` (date)

## Database: Knowledge
- `Title` (title, required)
- `Knowledge ID` (rich_text, unique)
- `Record Type` (select: SPEC/RUN/Meeting/Research/Deliverable/Agent/FAQ, required)
- `GitHub Canonical Link` (url, required)
- `Summary` (rich_text, required)
- `Status` (select: Draft/Review/Approved/Published)
- `Owner` (person)
- `Project` (relation -> Projects)
- `Task` (relation -> Tasks)
- `Source Path` (rich_text: repo-relative path)
- `Version` (rich_text)
- `Last Sync` (date)

## 必須ルール
- Deliverable は必ず `GitHub Canonical Link` を持つ。
- FAQ/軽メモ以外は Canonical Link 必須。
- Notion本文を正本にする場合は `Record Type=FAQ` かつ理由を `Summary` に明記。
