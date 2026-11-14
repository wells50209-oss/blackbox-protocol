# 黑箱協議 BLACKBOX PROTOCOL

6 人心理戰策略遊戲：在資訊不完整、其他玩家可能欺騙、系統估計也可能出錯的情況下，靠交易、承諾、背叛、攻擊與情報爭取最高 VP。

- 1 名玩家對上 5 名 AI，共 8 回合，每回合 3 AP
- 18 種隱藏目標，每局抽 6 種；可選「隨機模式」或「選擇模式」
- 風險星級、行為異常、三色情報、本回合攻擊預測

## 線上遊玩

部署到 GitHub Pages 後，網址會是：

```
https://<你的帳號>.github.io/<儲存庫名稱>/
```

## 加到手機主畫面（像 App 一樣玩）

用 GitHub Pages 的網址開啟後：

- **iPhone／iPad：** 用 Safari 開啟 → 分享按鈕 →「加入主畫面」
- **Android：** 用 Chrome 開啟 → 右上角選單 →「安裝應用程式」或「加到主畫面」

之後從主畫面圖示開啟會全螢幕、沒有瀏覽器框；第一次開啟後，沒有網路也能玩。

> 直接雙擊本機的 `index.html` 只能在瀏覽器裡玩，無法安裝到主畫面；安裝功能需要 `https://` 網址（例如 GitHub Pages）。

## 接收玩家回饋（Google 表單）

遊戲結算畫面有「給作者回饋」按鈕，玩家可以給 1～5 星、寫意見，並選擇附上本局摘要。回饋會送進你的 Google 表單，你在表單的「回覆」分頁查看，也可以連到 Google 試算表，或開啟「新回覆時寄電子郵件給我」。

設定方式：

1. 到 Google 表單建立新表單，**依序**建立三個題目：
   1. 「評分」：簡答
   2. 「意見」：段落
   3. 「本局摘要」：段落
   題目都不要設成「必填」。
2. 右上角「⋮」→「取得預先填入的連結」，三題分別填 `1`、`2`、`3`，按「取得連結」→「複製連結」。
3. 打開 `index.html`，找到這一行，把連結貼進引號裡：

   ```js
   const FEEDBACK_PREFILL_LINK = '';
   ```

4. 把 `sw.js` 第一行的 `VERSION` 改成新的版本號，重新上傳 `index.html` 和 `sw.js` 到 GitHub。

沒有設定時，玩家按送出會看到「作者尚未設定回饋表單」。

## 檔案

| 檔案 | 用途 |
|---|---|
| `index.html` | 網頁版遊戲（單一檔案，不需要安裝任何東西） |
| `python/blackbox_protocol.py` | Python 版：平衡模擬、圖表、PDF 報告與文字介面遊玩 |
| `manifest.webmanifest` | 主畫面安裝設定（名稱、圖示、全螢幕） |
| `sw.js` | 離線快取：第一次開啟後沒有網路也能玩 |
| `icons/` | 主畫面與瀏覽器分頁圖示 |
| `.nojekyll` | 讓 GitHub Pages 直接提供檔案，不經過 Jekyll 處理 |

## 本機遊玩

直接用瀏覽器開啟 `index.html` 即可，不需要網路伺服器。沒有網路時標題字型會改用系統字型，遊戲功能不受影響。

## Python 版

需要 Python 3.10 以上；圖表與 PDF 報告需要 matplotlib。

```bash
pip install matplotlib

# 自動模擬（預設 1000 局），輸出報告 PDF 並跳出圖表
python python/blackbox_protocol.py 10000 --seed 42

# 文字介面手動遊玩
python python/blackbox_protocol.py --play
```

常用參數：`--seed 42` 固定亂數、`--noplot` 不畫圖、`--nostrat` 略過單一策略測試、`--noexport` 不輸出 PDF、`--svg` 另存 SVG。

## 調整規則

所有規則數值都在 `blackbox_protocol.py` 開頭的常數區（例如 `GOAL_VP`、`ATK_GAIN`、`DEFEND_BONUS`）。網頁版的數值在 `index.html` 裡的 `const K=`、`GV=`、`GL=` 三段，改規則時兩邊要一起改。

更新網頁版後，請把 `sw.js` 第一行的 `VERSION`（例如 `blackbox-v1` → `blackbox-v2`）改掉，已安裝到主畫面的玩家下次開啟才會換成新版。
