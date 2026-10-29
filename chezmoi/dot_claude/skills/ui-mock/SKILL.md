---
description: UI の画面案・モック・実装イメージを HTML/CSS で組み、headless Chromium で撮って show_image でチャットに表示する。「イメージを見せて」「画面案を画像で」「モックを作って」「実装案を見せて」で使う。生成 AI は使わない。
argument-hint: [画面の説明]
---

## 方針

- 画像生成 AI は使わない。HTML/CSS で組んで撮る。文言・余白・配色を正確に指定でき、そのまま実装の土台になる。
- 既定では一時フォルダに作って表示するだけで、保存も片付けもしない。表示した画像は show-your-work が履歴として保持し、プレイヤーの History から辿れる。
- 「残して」と言われたとき、または依頼に含まれていたときだけ `~/dev/mocks/<リポジトリ名>/<画面名>.html` に HTML と PNG を保存する（リポジトリ名は `basename "$(git rev-parse --show-toplevel)"`）。プロジェクト内には置かない。

## 手順

1. 依頼から画面の構成を決める。既存 UI の再現なら貼られたスクリーンショットの配置・色・文言に合わせる。複数案は案ごとに HTML を分け、1 案 1 枚で撮って順に表示する。
2. HTML を 1 ファイルで書く（CSS・データ・JS を埋め込み、外部読み込みなし）。置き場所はセッションの scratchpad。`<body>` に `width`/`height` を固定し、撮影サイズと一致させる。日本語フォントは `"Hiragino Sans","Hiragino Kaku Gothic ProN",sans-serif` を指定する。
3. Playwright のキャッシュにある headless Chromium で撮る。npx や新規インストールはしない。

   ```sh
   BIN=$(find ~/Library/Caches/ms-playwright -type f -name chrome-headless-shell | sort | tail -1)
   "$BIN" --headless --disable-gpu --hide-scrollbars --window-size=1500,980 \
     --screenshot="$OUT.png" "file://$OUT.html"
   ```

   `--window-size` は `<body>` のサイズに合わせる。既定は 1500×980、モバイル画面は 390×844 を横に並べる。
4. 撮った PNG を自分で Read して崩れ（文字のはみ出し、重なり、フォント欠け）がないか確認してから、`show_image` で表示する。`title` に画面名を入れる。前の版を直したときは `previous` に前の #id を渡して History につなげる。
5. 修正依頼は HTML を直して同じ手順で撮り直す。作り直さない。

## やらないこと

- Figma の generate_image や Weave、codex の image_gen を呼ばない（別途頼まれたときだけ）。
- プロジェクトのディレクトリに HTML や PNG を書かない。
- ブラウザで開くよう頼んだり、localhost の URL を案内したりしない。チャットに出すところまでが仕事。
