[https://yiningsxu.github.io/id_photo_converter/](https://yiningsxu.github.io/id_photo_converter/)

# ID Photo Print Layout Converter

Languages: English | [中文](#中文说明) | [日本語](#日本語)

A fully static GitHub Pages tool for creating printable ID photo sheets in the browser. It can detect common finished ID photo sizes, fit the uploaded image into a fixed photo frame, arrange as many copies as possible on the selected paper size, and export printable PNG, JPG/JPEG, TIFF, and PDF files.

## Features

- Upload browser-decodable JPEG/JPG, PNG, WebP, BMP, TIFF, GIF, HEIC, or HEIF images.
- Auto-detect common finished ID photo sizes, or choose from built-in presets.
- Presets include Japan passport/My Number, US passport/visa, Mainland China passport/visa, Japan residence card, Japan driver license, Mainland China resident ID card, and more.
- Manually enter the finished photo size when auto-detection is uncertain.
- Set print paper size, for example postcard `100 mm x 148 mm`.
- Convert millimetres to print pixels by DPI. The default output is `600 DPI`.
- Adjust horizontal and vertical crop position with sliders.
- Scale and drag the uploaded image inside the fixed finished photo frame in the preview, then confirm to regenerate previews and download links.
- Automatically compute the best layout, such as `2 x 3` or `2 x 2`.
- Preview both the single finished photo and the full print sheet.
- Download printable `PNG`, `JPG/JPEG`, `TIFF`, and exact-size `PDF` files.
- No Python backend is required. Image processing, layout, and multi-format export all run locally in the browser.
- English, Chinese, and Japanese UI are available. English is shown by default.

## GitHub Pages Deployment

1. Push this directory to a GitHub repository.
2. In the repository, open `Settings` -> `Pages`.
3. Choose `Deploy from a branch`.
4. Select the `main` branch and `/root` directory.
5. Save the setting and open the GitHub Pages URL.

The entry point is the root `index.html`, which can be hosted directly by GitHub Pages.

## Local Preview

Open `index.html` directly in a browser, or start a static server:

```bash
python3 -m http.server 8000
```

Then visit:

```text
http://127.0.0.1:8000
```

The retained `app.py` and `converter.py` files are legacy Flask backend compatibility files and are not required for the current GitHub Pages version.

## Parameters

| Parameter | Description |
|---|---|
| Auto-detect uploaded photo size | Enabled by default. The browser first checks JPEG EXIF/JFIF or PNG pHYs DPI metadata, then falls back to common ID photo sizes and pixel dimensions. |
| Common size preset | Fills the photo width and height with a known ID photo size. |
| Finished photo width / height | Physical size of one finished ID photo, in mm. |
| Image size / position in frame | Adjusts how large the uploaded image appears inside the fixed finished photo frame. `100%` matches the original fill behavior, smaller values show more of the source image with white margins when needed, and larger values crop further inside the frame. Drag the single-photo preview or use the direction buttons to fine-tune position. |
| Print paper width / height | Physical paper size, in mm. For postcard paper, use `100 x 148`. |
| DPI | Output resolution. Use `300` for smaller files, `600` for the default high-quality output, or higher when the source image supports it. |
| Margin | Minimum paper margin, in mm. |
| Photo gap | Space between adjacent photos, in mm. |
| Auto-select paper orientation | Allows `100 x 148` to become `148 x 100` when that fits more copies. |
| Allow photo rotation | Allows each photo to rotate 90 degrees on the sheet to fit more copies. |
| Show cut border | Draws a 1 px cutting guide around each photo. |

## Size Presets

| Size | Common use |
|---|---|
| `35 x 45 mm` | Japan passport/My Number, South Korea passport/resident registration card, Taiwan passport/ID card, many European IDs |
| `51 x 51 mm` | US passport, visa, DV, and USCIS common photos |
| `33 x 48 mm` | Mainland China passport, travel document, Chinese visa |
| `30 x 40 mm` | Japan residence card and immigration submission photo |
| `24 x 30 mm` | Japan driver license |
| `26 x 32 mm` | Mainland China resident ID card, Spain DNI/passport common portrait format |

## Printing Notes

Prefer downloading the PDF for printing. In the print dialog, choose:

- `Actual size` / `100%`
- Do not choose `Fit to page`
- Do not let the printer driver scale the page automatically

If your printer does not support borderless postcard printing, set enough margin in the page, such as `3 mm` to `5 mm`.

## Output Quality

- `PDF` embeds a lossless RGB image. The file can be larger than a compressed PDF, but avoids extra JPEG compression.
- `PNG` and `TIFF` are lossless.
- `JPG/JPEG` uses the highest browser-supported quality, but JPEG is still a lossy format.
- Final quality depends on the source image pixels and the chosen DPI. For example, `35 x 45 mm` at `600 DPI` outputs one photo at about `827 x 1063 px`.

## Core Algorithm

1. Try to infer the finished ID photo size from image DPI metadata or common pixel-size matches.
2. Convert the finished photo size and paper size from `mm / 25.4 x DPI` into pixels.
3. Fit the uploaded image into the fixed finished photo frame without non-uniform stretching.
4. Apply the confirmed image scale inside that fixed frame.
5. Use the horizontal and vertical position sliders to decide which source area stays visible when cropping is needed.
6. Calculate the maximum rows and columns that fit the selected paper, margin, and gap.
7. Place all photo copies centered on a white sheet.
8. Export PNG/JPG/TIFF and generate an exact physical-size PDF.

## Limitations

- Auto-detection is based on DPI metadata, common presets, and pixel dimensions. When uncertain, it keeps the manual size.
- This version does not do face detection or automatic head centering. Use the position and image-size controls to adjust the photo.
- HEIC/HEIF decoding depends on the user's browser. Convert to JPEG or PNG first if unsupported.
- Browser previews are scaled for display and do not represent physical size on screen. The downloaded PDF/PNG/JPG/TIFF files are the printable output.
- The GitHub Pages version does not upload photos to a server and does not generate files inside the project `outputs/` directory.

## 中文说明

[Back to English](#id-photo-print-layout-converter) | [日本語](#日本語)

这是一个纯静态 GitHub Pages 工具。它可以在浏览器本地自动识别上传证件照的常见成品尺寸，把上传图像放进固定成品尺寸框，按指定纸张尺寸自动计算一张纸上能放下的最大张数，并导出可打印 PNG、JPG/JPEG、TIFF 和 PDF。

### 功能

- 上传浏览器可解码的 JPEG/JPG、PNG、WebP、BMP、TIFF、GIF、HEIC/HEIF 等常见图片格式。
- 自动识别常见证件照成品尺寸，也可从预设规格中一键选择。
- 预设包含日本护照/My Number、美国护照/签证、中国大陆护照/签证、日本在留卡、日本驾照、中国大陆居民身份证等常用尺寸。
- 识别不确定时仍可手动输入证件照成品尺寸。
- 输入打印纸尺寸，例如 postcard `100 mm x 148 mm`。
- 自动按 DPI 换算打印像素，默认 `600 DPI`。
- 通过水平 / 垂直位置滑块调整保留区域。
- 在预览里调整固定成品尺寸内的图像大小，确认后重新生成预览和下载链接。
- 自动计算最佳排版，例如 `2 x 3`、`2 x 2`。
- 输出单张证件照预览和打印纸排版预览。
- 下载可打印 `PNG`、`JPG/JPEG`、`TIFF` 和精确纸张尺寸的 `PDF`。
- 不需要 Python 后端；图片处理、排版和多格式文件生成都在浏览器中完成。
- 提供英语、中文、日语界面，默认显示英语。

### GitHub Pages 部署

1. 将本目录推送到 GitHub 仓库。
2. 在仓库 `Settings` -> `Pages` 中选择 `Deploy from a branch`。
3. Branch 选择 `main`，目录选择 `/root`。
4. 保存后访问 GitHub Pages 给出的地址。

入口文件是根目录的 `index.html`，可以直接被 GitHub Pages 托管。

### 本地预览

直接双击打开 `index.html` 即可。也可以启动一个静态服务器：

```bash
python3 -m http.server 8000
```

然后访问：

```text
http://127.0.0.1:8000
```

项目中保留的 `app.py` / `converter.py` 是旧版 Flask 后端兼容文件，不再是 GitHub Pages 运行所必需。

### 参数说明

| 参数 | 说明 |
|---|---|
| 自动识别上传图尺寸 | 默认开启。优先读取 JPEG EXIF/JFIF 或 PNG pHYs 的 DPI 元数据；没有可靠 DPI 时，根据常见证件照规格和像素尺寸匹配。 |
| 常用规格预设 | 选择后会自动填写证件照宽度 / 高度，并切换为该预设尺寸。 |
| 证件照宽度 / 高度 | 单张证件照的最终物理尺寸，单位 mm。 |
| 固定框内图像大小 | 在预览区调整上传图像放进单张成品尺寸后的缩放比例。`100%` 等同于原来的铺满效果，调小会尽量显示更多原图并在需要时留白，调大会在固定框内进一步裁切。 |
| 打印纸宽度 / 高度 | 打印纸物理尺寸，单位 mm。Postcard 可填 `100 x 148`。 |
| DPI | 输出分辨率。默认 `600`。如果文件过大可改为 `300`，如果原图足够清晰且需要更高质量可继续调高。 |
| 页边距 | 排版时保留的最小边距，单位 mm。 |
| 照片间距 | 相邻证件照之间的间距，单位 mm。 |
| 自动选择纸张横竖方向 | 允许输出纸张从 `100 x 148` 自动切换为 `148 x 100`，以容纳更多张。 |
| 允许单张证件照旋转 | 允许每张证件照在纸上旋转 90 度。剪下后再转正即可；不希望照片横放时请关闭。 |
| 显示裁切边框 | 给每张照片画一圈 1 px 的裁切参考线。 |

### 证件照尺寸预设

| 尺寸 | 适用证件 |
|---|---|
| `35 x 45 mm` | 日本护照/My Number、韩国护照/居民登记证、台湾护照/身分证、法国/德国/意大利等多数欧洲证件 |
| `51 x 51 mm` | 美国护照/签证/DV/USCIS 常见照片 |
| `33 x 48 mm` | 中国大陆护照/旅行证/中国签证 |
| `30 x 40 mm` | 日本在留卡/入管提交照 |
| `24 x 30 mm` | 日本驾照 |
| `26 x 32 mm` | 中国大陆居民身份证、西班牙 DNI/护照常用竖版 |

### 打印注意事项

优先下载 PDF 打印。打印时必须选择：

- `Actual size` / `实际大小` / `100%`
- 不要选择 `Fit to page` / `适合页面`
- 不要让打印机驱动自动缩放

如果打印机不支持无边距 postcard 打印，请在页面里设置足够的页边距，例如 `3 mm` 到 `5 mm`。

### 核心算法

1. 在浏览器中尝试从图片 DPI 元数据或常见证件照像素规格识别成品尺寸。
2. 根据 `mm / 25.4 x DPI` 把目标物理尺寸转换为像素。
3. 将上传图像等比例放进固定单张成品画布，不做横向或纵向拉伸。
4. 按预览中确认的图像缩放比例调整画布内图像大小。
5. 通过水平 / 垂直位置滑块决定裁切时保留的原图区域。
6. 根据纸张尺寸、页边距、照片间距计算可放置的最大列数和行数。
7. 将所有照片居中排布到白色画布。
8. 输出 PNG/JPG/TIFF，并生成精确物理页面尺寸的 PDF。

### 限制

- 自动识别基于 DPI 元数据、常见规格和像素尺寸，无法可靠判断时会保留手动尺寸。
- 这个版本不做人脸检测或自动居中，请使用位置和图像大小控件调整照片。
- HEIC/HEIF 取决于用户浏览器是否原生支持解码；不支持时请先转换为 JPEG 或 PNG。
- 浏览器中的预览图会缩小显示，不代表屏幕上的物理尺寸；下载的 PDF / PNG / JPG / TIFF 才是打印输出。
- GitHub Pages 版本不会上传照片到服务器，也不会在项目目录生成 `outputs/` 文件。

## 日本語

[Back to English](#id-photo-print-layout-converter) | [中文](#中文说明)

これは、ブラウザ内で動作する静的な GitHub Pages 用ツールです。アップロードした証明写真の一般的な仕上がりサイズを自動検出し、固定サイズの写真フレーム内に画像を配置し、指定した用紙にできるだけ多く並べて、印刷用の PNG、JPG/JPEG、TIFF、PDF を出力できます。

### 機能

- ブラウザで読み込める JPEG/JPG、PNG、WebP、BMP、TIFF、GIF、HEIC/HEIF 画像に対応。
- 一般的な証明写真サイズを自動検出、またはプリセットから選択。
- 日本パスポート/My Number、米国パスポート/ビザ、中国大陸パスポート/ビザ、日本在留カード、日本運転免許証、中国大陸居民身分証などのプリセットを用意。
- 自動検出が不確実な場合は、仕上がりサイズを手入力可能。
- postcard `100 mm x 148 mm` などの印刷用紙サイズを指定可能。
- DPI に基づいて mm を印刷ピクセルへ変換。既定は `600 DPI`。
- 水平 / 垂直位置スライダーで表示位置を調整。
- プレビュー内で固定仕上がりサイズ内の画像サイズを調整し、確定後にプレビューとダウンロードリンクを再生成。
- `2 x 3`、`2 x 2` など、最適な配置を自動計算。
- 1 枚の証明写真プレビューと印刷用紙レイアウトプレビューを表示。
- 印刷用 `PNG`、`JPG/JPEG`、`TIFF`、正確な用紙サイズの `PDF` をダウンロード。
- Python バックエンド不要。画像処理、レイアウト、多形式出力はすべてブラウザ内で完結。
- 英語、中国語、日本語 UI に対応。既定表示は英語。

### GitHub Pages へのデプロイ

1. このディレクトリを GitHub リポジトリへ push します。
2. リポジトリの `Settings` -> `Pages` を開きます。
3. `Deploy from a branch` を選択します。
4. Branch は `main`、ディレクトリは `/root` を選択します。
5. 保存後、表示された GitHub Pages URL を開きます。

入口ファイルはルートの `index.html` で、そのまま GitHub Pages でホストできます。

### ローカルプレビュー

`index.html` を直接ブラウザで開くか、静的サーバーを起動します。

```bash
python3 -m http.server 8000
```

その後、次の URL を開きます。

```text
http://127.0.0.1:8000
```

残っている `app.py` / `converter.py` は旧 Flask バックエンド互換ファイルで、現在の GitHub Pages 版には必要ありません。

### パラメータ

| パラメータ | 説明 |
|---|---|
| アップロード画像サイズの自動検出 | 既定で有効。JPEG EXIF/JFIF または PNG pHYs の DPI メタデータを優先し、信頼できない場合は一般的な証明写真サイズとピクセル寸法で照合します。 |
| よく使うサイズ | 選択した証明写真の幅 / 高さを自動入力します。 |
| 仕上がり写真の幅 / 高さ | 1 枚の証明写真の物理サイズ。単位は mm。 |
| 枠内の画像サイズ | 固定仕上がりフレーム内でアップロード画像をどれだけ大きく表示するかを調整します。`100%` は従来の全面表示、値を小さくするとより広い範囲を表示して必要に応じて白余白が入り、大きくするとさらにトリミングされます。 |
| 用紙の幅 / 高さ | 印刷用紙の物理サイズ。単位は mm。Postcard は `100 x 148`。 |
| DPI | 出力解像度。既定は `600`。ファイルを小さくしたい場合は `300`、元画像が十分高解像度ならより高い値も指定できます。 |
| 余白 | 用紙に残す最小余白。単位は mm。 |
| 写真間隔 | 隣り合う写真の間隔。単位は mm。 |
| 用紙の向きを自動選択 | より多く配置できる場合、`100 x 148` を `148 x 100` に切り替えます。 |
| 写真の回転を許可 | より多く配置するため、各写真を用紙上で 90 度回転できます。 |
| カット用の枠線を表示 | 各写真の周囲に 1 px のカットガイドを描画します。 |

### サイズプリセット

| サイズ | 主な用途 |
|---|---|
| `35 x 45 mm` | 日本パスポート/My Number、韓国パスポート/住民登録証、台湾パスポート/身分証、欧州の多くの証明写真 |
| `51 x 51 mm` | 米国パスポート、ビザ、DV、USCIS 向け写真 |
| `33 x 48 mm` | 中国大陸パスポート、旅行証、中国ビザ |
| `30 x 40 mm` | 日本在留カード、入管提出用写真 |
| `24 x 30 mm` | 日本運転免許証 |
| `26 x 32 mm` | 中国大陸居民身分証、スペイン DNI/パスポート縦型 |

### 印刷時の注意

印刷には PDF のダウンロードを推奨します。印刷ダイアログでは次を選択してください。

- `Actual size` / `100%`
- `Fit to page` は選択しない
- プリンタードライバーによる自動拡大縮小を使わない

プリンターがフチなし postcard 印刷に対応していない場合は、ページ側で `3 mm` から `5 mm` 程度の余白を設定してください。

### コアアルゴリズム

1. 画像の DPI メタデータ、または一般的なピクセル寸法から証明写真サイズを推定します。
2. `mm / 25.4 x DPI` により、仕上がり写真サイズと用紙サイズをピクセルへ変換します。
3. アップロード画像を固定仕上がりフレームへ縦横比を保ったまま配置します。
4. 確定された画像スケールを固定フレーム内に適用します。
5. 水平 / 垂直位置スライダーで、トリミング時に残す元画像範囲を決めます。
6. 用紙サイズ、余白、写真間隔から最大の行数と列数を計算します。
7. 白い用紙キャンバスの中央に写真を配置します。
8. PNG/JPG/TIFF を出力し、正確な物理サイズの PDF を生成します。

### 制限

- 自動検出は DPI メタデータ、一般的なプリセット、ピクセル寸法に基づきます。不確実な場合は手入力サイズを使用します。
- 顔検出や自動センタリングは行いません。位置と画像サイズのコントロールで調整してください。
- HEIC/HEIF の読み込み可否はブラウザに依存します。未対応の場合は JPEG または PNG に変換してください。
- ブラウザ上のプレビューは表示用に縮小されるため、画面上の物理サイズを示すものではありません。印刷にはダウンロードした PDF / PNG / JPG / TIFF を使用してください。
- GitHub Pages 版では写真をサーバーへアップロードせず、プロジェクト内の `outputs/` ディレクトリにもファイルを生成しません。
