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

## 檔案

| 檔案 | 用途 |
|---|---|
| `index.html` | 網頁版遊戲（單一檔案，不需要安裝任何東西） |
| `python/blackbox_protocol.py` | Python 版：平衡模擬、圖表、PDF 報告與文字介面遊玩 |
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
