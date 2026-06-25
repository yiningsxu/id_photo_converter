from __future__ import annotations

import base64
import io
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import BinaryIO, Dict, Optional, Tuple

from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

try:
    from pillow_heif import register_heif_opener
except Exception:  # pragma: no cover - optional format support
    register_heif_opener = None
else:  # pragma: no cover - depends on optional native package
    register_heif_opener()

try:
    from reportlab.lib.units import mm as PDF_MM
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
except Exception:  # pragma: no cover - handled at runtime
    PDF_MM = None
    ImageReader = None
    canvas = None


MM_PER_INCH = 25.4
COMMON_PRINT_DPIS = (300, 350, 600)


@dataclass(frozen=True)
class PhotoSizePreset:
    name: str
    width_mm: float
    height_mm: float


@dataclass(frozen=True)
class DetectedPhotoSize:
    width_mm: float
    height_mm: float
    label: str
    confidence: str
    source: str
    estimated_dpi: Optional[float]
    message: str

    def public_dict(self) -> Dict[str, object]:
        return {
            "width_mm": self.width_mm,
            "height_mm": self.height_mm,
            "label": self.label,
            "confidence": self.confidence,
            "source": self.source,
            "estimated_dpi": round(self.estimated_dpi, 1)
            if self.estimated_dpi is not None
            else None,
            "message": self.message,
        }


PHOTO_SIZE_PRESETS = (
    PhotoSizePreset(
        "35x45 mm - 日本护照/My Number、韩国护照/居民登记证、台湾护照/身分证、欧洲多数证件",
        35.0,
        45.0,
    ),
    PhotoSizePreset(
        "51x51 mm - 美国护照/签证/DV/USCIS常见照片",
        51.0,
        51.0,
    ),
    PhotoSizePreset(
        "33x48 mm - 中国大陆护照/旅行证/中国签证",
        33.0,
        48.0,
    ),
    PhotoSizePreset(
        "30x40 mm - 日本在留卡/入管提交照",
        30.0,
        40.0,
    ),
    PhotoSizePreset("24x30 mm - 日本驾照", 24.0, 30.0),
    PhotoSizePreset(
        "26x32 mm - 中国大陆居民身份证、西班牙DNI/护照常用竖版",
        26.0,
        32.0,
    ),
)


@dataclass(frozen=True)
class LayoutPlan:
    dpi: int
    target_photo_w_mm: float
    target_photo_h_mm: float
    paper_w_mm: float
    paper_h_mm: float
    requested_paper_w_mm: float
    requested_paper_h_mm: float
    margin_mm: float
    gap_mm: float
    photo_cell_w_px: int
    photo_cell_h_px: int
    photo_unrotated_w_px: int
    photo_unrotated_h_px: int
    paper_w_px: int
    paper_h_px: int
    margin_px: int
    gap_px: int
    cols: int
    rows: int
    count: int
    grid_w_px: int
    grid_h_px: int
    start_x_px: int
    start_y_px: int
    photo_rotated_on_sheet: bool
    paper_orientation_swapped: bool
    used_area_ratio: float

    def public_dict(self) -> Dict[str, object]:
        data = asdict(self)
        data["grid"] = f"{self.cols} x {self.rows}"
        data["copies"] = self.count
        data["paper_px"] = f"{self.paper_w_px} x {self.paper_h_px}"
        data["photo_cell_px"] = f"{self.photo_cell_w_px} x {self.photo_cell_h_px}"
        data["photo_print_px_before_optional_rotation"] = (
            f"{self.photo_unrotated_w_px} x {self.photo_unrotated_h_px}"
        )
        return data


@dataclass(frozen=True)
class ConversionResult:
    cropped_photo: Image.Image
    print_photo: Image.Image
    layout_sheet: Image.Image
    crop_box: Tuple[int, int, int, int]
    plan: LayoutPlan


def mm_to_px(value_mm: float, dpi: int) -> int:
    """Convert millimetres to pixels at a given DPI."""
    return max(1, int(round(value_mm / MM_PER_INCH * dpi)))


def _format_mm(value_mm: float) -> str:
    rounded = round(value_mm, 1)
    if abs(rounded - round(rounded)) < 1e-9:
        return str(int(round(rounded)))
    return f"{rounded:.1f}"


def _extract_dpi(image: Image.Image) -> Optional[Tuple[float, float]]:
    """Read usable horizontal and vertical DPI from common image metadata."""
    raw_dpi = image.info.get("dpi")
    if isinstance(raw_dpi, tuple) and len(raw_dpi) >= 2:
        try:
            dpi_x = float(raw_dpi[0])
            dpi_y = float(raw_dpi[1])
        except (TypeError, ValueError):
            dpi_x = dpi_y = 0.0
        if dpi_x > 0 and dpi_y > 0 and math.isfinite(dpi_x) and math.isfinite(dpi_y):
            return dpi_x, dpi_y

    jfif_unit = image.info.get("jfif_unit")
    jfif_density = image.info.get("jfif_density")
    if isinstance(jfif_density, tuple) and len(jfif_density) >= 2 and jfif_unit in {1, 2}:
        try:
            dpi_x = float(jfif_density[0])
            dpi_y = float(jfif_density[1])
        except (TypeError, ValueError):
            return None
        if jfif_unit == 2:
            dpi_x *= 2.54
            dpi_y *= 2.54
        if dpi_x > 0 and dpi_y > 0 and math.isfinite(dpi_x) and math.isfinite(dpi_y):
            return dpi_x, dpi_y

    return None


def _oriented_presets():
    for preset in PHOTO_SIZE_PRESETS:
        yield preset, preset.width_mm, preset.height_mm, False
        if abs(preset.width_mm - preset.height_mm) > 1e-9:
            yield preset, preset.height_mm, preset.width_mm, True


def _nearest_preset_by_mm(width_mm: float, height_mm: float):
    best = None
    for preset, preset_w_mm, preset_h_mm, rotated in _oriented_presets():
        width_error = abs(width_mm - preset_w_mm) / preset_w_mm
        height_error = abs(height_mm - preset_h_mm) / preset_h_mm
        max_abs_error_mm = max(abs(width_mm - preset_w_mm), abs(height_mm - preset_h_mm))
        score = max(width_error, height_error)
        candidate = (score, max_abs_error_mm, preset, preset_w_mm, preset_h_mm, rotated)
        if best is None or candidate[:2] < best[:2]:
            best = candidate
    return best


def _is_plausible_photo_mm(width_mm: float, height_mm: float) -> bool:
    short_side = min(width_mm, height_mm)
    long_side = max(width_mm, height_mm)
    return 15.0 <= short_side <= 80.0 and 20.0 <= long_side <= 90.0


def _detected_label(preset: PhotoSizePreset, width_mm: float, height_mm: float) -> str:
    return f"{preset.name}（{_format_mm(width_mm)} x {_format_mm(height_mm)} mm）"


def _detect_from_dpi_metadata(image: Image.Image) -> Optional[DetectedPhotoSize]:
    dpi = _extract_dpi(image)
    if dpi is None:
        return None

    dpi_x, dpi_y = dpi
    width_mm = image.width / dpi_x * MM_PER_INCH
    height_mm = image.height / dpi_y * MM_PER_INCH
    if not _is_plausible_photo_mm(width_mm, height_mm):
        return None

    estimated_dpi = (dpi_x + dpi_y) / 2
    nearest = _nearest_preset_by_mm(width_mm, height_mm)
    if nearest is not None:
        score, max_abs_error_mm, preset, preset_w_mm, preset_h_mm, _ = nearest
        if score <= 0.04 or max_abs_error_mm <= 1.2:
            label = _detected_label(preset, preset_w_mm, preset_h_mm)
            return DetectedPhotoSize(
                width_mm=preset_w_mm,
                height_mm=preset_h_mm,
                label=label,
                confidence="high",
                source="dpi_metadata",
                estimated_dpi=estimated_dpi,
                message=f"已根据图片 DPI 元数据识别为 {label}。",
            )

    measured_w_mm = round(width_mm, 1)
    measured_h_mm = round(height_mm, 1)
    label = f"自定义尺寸（{_format_mm(measured_w_mm)} x {_format_mm(measured_h_mm)} mm）"
    return DetectedPhotoSize(
        width_mm=measured_w_mm,
        height_mm=measured_h_mm,
        label=label,
        confidence="medium",
        source="dpi_metadata",
        estimated_dpi=estimated_dpi,
        message=f"已根据图片 DPI 元数据识别为 {label}。",
    )


def _candidate_ratio_key(width_mm: float, height_mm: float) -> int:
    ratio = width_mm / height_mm
    return int(round(ratio * 1000))


def _detect_from_pixel_dimensions(image: Image.Image) -> Optional[DetectedPhotoSize]:
    candidates = []
    ratio_matches = []
    source_ratio = image.width / image.height

    for preset, width_mm, height_mm, _ in _oriented_presets():
        target_ratio = width_mm / height_mm
        ratio_error = abs(source_ratio - target_ratio) / target_ratio
        if ratio_error <= 0.008:
            ratio_matches.append((preset.name, _candidate_ratio_key(width_mm, height_mm)))

        estimated_dpi_x = image.width * MM_PER_INCH / width_mm
        estimated_dpi_y = image.height * MM_PER_INCH / height_mm
        estimated_dpi = (estimated_dpi_x + estimated_dpi_y) / 2
        if estimated_dpi <= 0:
            continue

        dpi_balance_error = abs(estimated_dpi_x - estimated_dpi_y) / estimated_dpi
        nearest_common_dpi = min(
            COMMON_PRINT_DPIS,
            key=lambda common_dpi: abs(estimated_dpi - common_dpi) / common_dpi,
        )
        common_dpi_error = abs(estimated_dpi - nearest_common_dpi) / nearest_common_dpi
        expected_w_px = width_mm / MM_PER_INCH * nearest_common_dpi
        expected_h_px = height_mm / MM_PER_INCH * nearest_common_dpi
        pixel_error = max(
            abs(image.width - expected_w_px) / expected_w_px,
            abs(image.height - expected_h_px) / expected_h_px,
        )
        score = (dpi_balance_error * 4) + (common_dpi_error * 2) + pixel_error
        candidates.append(
            (
                score,
                dpi_balance_error,
                common_dpi_error,
                ratio_error,
                estimated_dpi,
                preset,
                width_mm,
                height_mm,
            )
        )

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[:4])
    (
        _score,
        dpi_balance_error,
        common_dpi_error,
        ratio_error,
        estimated_dpi,
        preset,
        width_mm,
        height_mm,
    ) = candidates[0]

    label = _detected_label(preset, width_mm, height_mm)
    if dpi_balance_error <= 0.025 and common_dpi_error <= 0.035:
        return DetectedPhotoSize(
            width_mm=width_mm,
            height_mm=height_mm,
            label=label,
            confidence="high",
            source="pixel_match",
            estimated_dpi=estimated_dpi,
            message=f"已根据像素尺寸识别为 {label}。",
        )

    if (
        ratio_error <= 0.008
        and dpi_balance_error <= 0.025
        and 250 <= estimated_dpi <= 650
        and len(ratio_matches) == 1
    ):
        return DetectedPhotoSize(
            width_mm=width_mm,
            height_mm=height_mm,
            label=label,
            confidence="medium",
            source="aspect_ratio",
            estimated_dpi=estimated_dpi,
            message=f"已根据长宽比识别为 {label}。",
        )

    return None


def detect_photo_size(image: Image.Image) -> Optional[DetectedPhotoSize]:
    """
    Infer the finished physical size of an uploaded ID photo.

    The detector first trusts usable DPI metadata. If metadata is missing or
    implausible, it matches the image's pixel dimensions against common ID photo
    sizes at print DPIs such as 300, 350, and 600.
    """
    return _detect_from_dpi_metadata(image) or _detect_from_pixel_dimensions(image)


def _positive_float(raw: object, field_name: str) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} 必须是数字。")
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{field_name} 必须大于 0。")
    return value


def _non_negative_float(raw: object, field_name: str) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} 必须是数字。")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{field_name} 不能小于 0。")
    return value


def validate_params(
    photo_w_mm: object,
    photo_h_mm: object,
    paper_w_mm: object,
    paper_h_mm: object,
    dpi: object,
    margin_mm: object,
    gap_mm: object,
) -> Tuple[float, float, float, float, int, float, float]:
    photo_w = _positive_float(photo_w_mm, "证件照宽度")
    photo_h = _positive_float(photo_h_mm, "证件照高度")
    paper_w = _positive_float(paper_w_mm, "打印纸宽度")
    paper_h = _positive_float(paper_h_mm, "打印纸高度")
    margin = _non_negative_float(margin_mm, "页边距")
    gap = _non_negative_float(gap_mm, "照片间距")

    try:
        dpi_int = int(dpi)
    except (TypeError, ValueError):
        raise ValueError("DPI 必须是整数。")
    if dpi_int < 72 or dpi_int > 1200:
        raise ValueError("DPI 建议设置在 72 到 1200 之间。")

    if paper_w <= 2 * margin or paper_h <= 2 * margin:
        raise ValueError("页边距过大，已经超过纸张可用区域。")

    return photo_w, photo_h, paper_w, paper_h, dpi_int, margin, gap


def load_uploaded_image(file_obj: BinaryIO) -> Image.Image:
    """Open an uploaded image and normalize EXIF orientation."""
    try:
        image = Image.open(file_obj)
        image_info = dict(image.info)
        if getattr(image, "is_animated", False):
            image.seek(0)
            image = image.copy()
        image = ImageOps.exif_transpose(image)
        image.load()
        converted = image.convert("RGB")
        converted.info.update(image_info)
        return converted
    except UnidentifiedImageError as exc:
        raise ValueError(
            "无法识别图片格式。请上传 JPEG/JPG、PNG、WebP、BMP、TIFF、GIF、HEIC 或 HEIF。"
        ) from exc
    except Exception as exc:
        raise ValueError(
            "无法读取图片。请确认文件没有损坏，并使用 JPEG/JPG、PNG、WebP、BMP、TIFF、GIF、HEIC 或 HEIF。"
        ) from exc


def crop_to_aspect(
    image: Image.Image,
    target_w_mm: float,
    target_h_mm: float,
    anchor_x: float = 0.5,
    anchor_y: float = 0.5,
) -> Tuple[Image.Image, Tuple[int, int, int, int]]:
    """
    Crop the image to match target aspect ratio without non-uniform scaling.

    anchor_x and anchor_y are 0..1. 0 means left/top, 1 means right/bottom.
    The crop is done on the original pixel grid before resizing for print.
    """
    if image.width <= 0 or image.height <= 0:
        raise ValueError("图片尺寸无效。")

    anchor_x = min(1.0, max(0.0, float(anchor_x)))
    anchor_y = min(1.0, max(0.0, float(anchor_y)))

    target_ratio = target_w_mm / target_h_mm
    source_ratio = image.width / image.height

    if source_ratio > target_ratio:
        # Source is too wide: crop left and right.
        crop_h = image.height
        crop_w = int(round(crop_h * target_ratio))
        crop_w = min(crop_w, image.width)
        left = int(round((image.width - crop_w) * anchor_x))
        top = 0
    else:
        # Source is too tall: crop top and bottom.
        crop_w = image.width
        crop_h = int(round(crop_w / target_ratio))
        crop_h = min(crop_h, image.height)
        left = 0
        top = int(round((image.height - crop_h) * anchor_y))

    right = left + crop_w
    bottom = top + crop_h
    crop_box = (left, top, right, bottom)
    return image.crop(crop_box), crop_box


def choose_layout(
    photo_w_mm: float,
    photo_h_mm: float,
    paper_w_mm: float,
    paper_h_mm: float,
    dpi: int,
    margin_mm: float,
    gap_mm: float,
    auto_paper_orientation: bool = True,
    allow_photo_rotation: bool = False,
) -> LayoutPlan:
    """Choose the layout with the largest number of photos on one sheet."""
    candidates = []
    paper_orientations = [(paper_w_mm, paper_h_mm, False)]
    if auto_paper_orientation and abs(paper_w_mm - paper_h_mm) > 1e-9:
        paper_orientations.append((paper_h_mm, paper_w_mm, True))

    photo_orientations = [(photo_w_mm, photo_h_mm, False)]
    if allow_photo_rotation and abs(photo_w_mm - photo_h_mm) > 1e-9:
        photo_orientations.append((photo_h_mm, photo_w_mm, True))

    for effective_paper_w_mm, effective_paper_h_mm, paper_swapped in paper_orientations:
        paper_w_px = mm_to_px(effective_paper_w_mm, dpi)
        paper_h_px = mm_to_px(effective_paper_h_mm, dpi)
        margin_px = mm_to_px(margin_mm, dpi) if margin_mm else 0
        gap_px = mm_to_px(gap_mm, dpi) if gap_mm else 0
        available_w_px = paper_w_px - 2 * margin_px
        available_h_px = paper_h_px - 2 * margin_px
        if available_w_px <= 0 or available_h_px <= 0:
            continue

        for cell_w_mm, cell_h_mm, photo_rotated in photo_orientations:
            cell_w_px = mm_to_px(cell_w_mm, dpi)
            cell_h_px = mm_to_px(cell_h_mm, dpi)
            cols = int((available_w_px + gap_px) // (cell_w_px + gap_px))
            rows = int((available_h_px + gap_px) // (cell_h_px + gap_px))
            if cols <= 0 or rows <= 0:
                continue

            grid_w_px = cols * cell_w_px + (cols - 1) * gap_px
            grid_h_px = rows * cell_h_px + (rows - 1) * gap_px
            start_x_px = (paper_w_px - grid_w_px) // 2
            start_y_px = (paper_h_px - grid_h_px) // 2
            count = cols * rows
            used_area_ratio = (grid_w_px * grid_h_px) / (paper_w_px * paper_h_px)

            plan = LayoutPlan(
                dpi=dpi,
                target_photo_w_mm=photo_w_mm,
                target_photo_h_mm=photo_h_mm,
                paper_w_mm=effective_paper_w_mm,
                paper_h_mm=effective_paper_h_mm,
                requested_paper_w_mm=paper_w_mm,
                requested_paper_h_mm=paper_h_mm,
                margin_mm=margin_mm,
                gap_mm=gap_mm,
                photo_cell_w_px=cell_w_px,
                photo_cell_h_px=cell_h_px,
                photo_unrotated_w_px=mm_to_px(photo_w_mm, dpi),
                photo_unrotated_h_px=mm_to_px(photo_h_mm, dpi),
                paper_w_px=paper_w_px,
                paper_h_px=paper_h_px,
                margin_px=margin_px,
                gap_px=gap_px,
                cols=cols,
                rows=rows,
                count=count,
                grid_w_px=grid_w_px,
                grid_h_px=grid_h_px,
                start_x_px=start_x_px,
                start_y_px=start_y_px,
                photo_rotated_on_sheet=photo_rotated,
                paper_orientation_swapped=paper_swapped,
                used_area_ratio=used_area_ratio,
            )
            # Primary score: more copies. Tie-breakers: avoid rotating photos, avoid swapping page,
            # then prefer a tighter grid.
            candidates.append(
                (
                    count,
                    0 if photo_rotated else 1,
                    0 if paper_swapped else 1,
                    used_area_ratio,
                    plan,
                )
            )

    if not candidates:
        raise ValueError("当前照片尺寸、纸张尺寸、页边距和间距无法排下任何一张证件照。")

    candidates.sort(key=lambda item: item[:4], reverse=True)
    return candidates[0][4]


def _draw_cut_marks(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> None:
    """Draw simple 1px cut guide around each photo cell."""
    draw.rectangle([x, y, x + w - 1, y + h - 1], outline=(40, 40, 40), width=1)


def build_print_sheet(
    image: Image.Image,
    photo_w_mm: float,
    photo_h_mm: float,
    paper_w_mm: float,
    paper_h_mm: float,
    dpi: int = 300,
    margin_mm: float = 3.0,
    gap_mm: float = 2.0,
    anchor_x: float = 0.5,
    anchor_y: float = 0.5,
    auto_paper_orientation: bool = True,
    allow_photo_rotation: bool = False,
    draw_cut_marks: bool = True,
) -> ConversionResult:
    """Crop, resize, and lay out the uploaded photo for printing."""
    plan = choose_layout(
        photo_w_mm=photo_w_mm,
        photo_h_mm=photo_h_mm,
        paper_w_mm=paper_w_mm,
        paper_h_mm=paper_h_mm,
        dpi=dpi,
        margin_mm=margin_mm,
        gap_mm=gap_mm,
        auto_paper_orientation=auto_paper_orientation,
        allow_photo_rotation=allow_photo_rotation,
    )

    cropped, crop_box = crop_to_aspect(
        image=image,
        target_w_mm=photo_w_mm,
        target_h_mm=photo_h_mm,
        anchor_x=anchor_x,
        anchor_y=anchor_y,
    )

    print_photo = cropped.resize(
        (plan.photo_unrotated_w_px, plan.photo_unrotated_h_px),
        Image.Resampling.LANCZOS,
    )
    if plan.photo_rotated_on_sheet:
        print_photo = print_photo.rotate(90, expand=True)

    sheet = Image.new("RGB", (plan.paper_w_px, plan.paper_h_px), "white")
    draw = ImageDraw.Draw(sheet)
    for row in range(plan.rows):
        for col in range(plan.cols):
            x = plan.start_x_px + col * (plan.photo_cell_w_px + plan.gap_px)
            y = plan.start_y_px + row * (plan.photo_cell_h_px + plan.gap_px)
            sheet.paste(print_photo, (x, y))
            if draw_cut_marks:
                _draw_cut_marks(draw, x, y, plan.photo_cell_w_px, plan.photo_cell_h_px)

    return ConversionResult(
        cropped_photo=cropped,
        print_photo=print_photo,
        layout_sheet=sheet,
        crop_box=crop_box,
        plan=plan,
    )


def image_to_data_url(image: Image.Image, max_side: int = 1200) -> str:
    """Return a small PNG data URL for browser preview."""
    preview = image.copy()
    preview.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    preview.save(buffer, format="PNG", optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def save_png(image: Image.Image, path: Path, dpi: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", dpi=(dpi, dpi))


def save_pdf(image: Image.Image, path: Path, plan: LayoutPlan) -> None:
    """Save the final sheet to a PDF page with exact physical page size."""
    if canvas is None or ImageReader is None or PDF_MM is None:
        raise RuntimeError("reportlab 未安装，无法生成 PDF。请运行：pip install reportlab")

    path.parent.mkdir(parents=True, exist_ok=True)
    page_w_pt = plan.paper_w_mm * PDF_MM
    page_h_pt = plan.paper_h_mm * PDF_MM

    img_buffer = io.BytesIO()
    image.save(img_buffer, format="PNG", dpi=(plan.dpi, plan.dpi))
    img_buffer.seek(0)

    pdf = canvas.Canvas(str(path), pagesize=(page_w_pt, page_h_pt))
    pdf.drawImage(
        ImageReader(img_buffer),
        0,
        0,
        width=page_w_pt,
        height=page_h_pt,
        preserveAspectRatio=False,
        mask="auto",
    )
    pdf.showPage()
    pdf.save()
