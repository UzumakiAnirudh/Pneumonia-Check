import io

import numpy as np
import pytest
import torch
from PIL import Image

from app.services.preprocessing import (
    IMAGENET_MEAN,
    IMAGENET_STD,
    ImageDecodeError,
    PreprocessConfig,
    encode_png_data_uri,
    load_image,
    make_display_image,
    prepare_uint8,
    preprocess,
    strip_dicom_identifiers,
)
from tests.conftest import encode


def test_preprocess_shape_and_channels(sample_bytes):
    img = load_image(sample_bytes["normal_01"])
    x = preprocess(img.gray)
    assert x.shape == (1, 3, 224, 224)
    assert x.dtype == torch.float32
    # Grayscale replicated to 3 channels => de-normalised channels are identical.
    denorm = x[0] * torch.tensor(IMAGENET_STD).view(3, 1, 1) + torch.tensor(IMAGENET_MEAN).view(3, 1, 1)
    assert torch.allclose(denorm[0], denorm[1], atol=1e-5)
    assert torch.allclose(denorm[1], denorm[2], atol=1e-5)
    assert 0.0 <= float(denorm.min()) and float(denorm.max()) <= 1.0 + 1e-5


def test_normalisation_values():
    gray = np.full((300, 300), 255, np.uint8)
    x = preprocess(gray, PreprocessConfig(use_clahe=False))
    expected = (1.0 - IMAGENET_MEAN[0]) / IMAGENET_STD[0]
    assert float(x[0, 0].mean()) == pytest.approx(expected, rel=1e-4)


def test_clahe_is_deterministic_and_toggleable(sample_bytes):
    gray = load_image(sample_bytes["viral_01"]).gray
    a = prepare_uint8(gray, PreprocessConfig(use_clahe=True))
    b = prepare_uint8(gray, PreprocessConfig(use_clahe=True))
    c = prepare_uint8(gray, PreprocessConfig(use_clahe=False))
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)
    assert a.shape == (224, 224) and a.dtype == np.uint8


def test_config_roundtrip():
    cfg = PreprocessConfig(image_size=256, use_clahe=False)
    assert PreprocessConfig.from_dict(cfg.to_dict()) == cfg
    assert PreprocessConfig.from_dict(None) == PreprocessConfig()


def test_rgb_input_converted_to_grayscale():
    rgb = np.zeros((400, 300, 3), np.uint8)
    rgb[..., 0] = 200
    img = load_image(encode(rgb))
    assert img.gray.shape == (400, 300)
    assert img.rgb.shape == (400, 300, 3)
    assert img.width == 300 and img.height == 400


def test_exif_metadata_is_discarded():
    arr = np.random.default_rng(0).integers(0, 255, (256, 256, 3), dtype=np.uint8)
    exif = Image.Exif()
    exif[0x010E] = "PATIENT John Doe"  # ImageDescription
    exif[0x0112] = 1
    data = encode(arr, "JPEG", exif=exif.tobytes())
    assert b"John Doe" in data
    img = load_image(data)
    uri = encode_png_data_uri(make_display_image(img.gray))
    import base64

    assert b"John Doe" not in base64.b64decode(uri.split(",", 1)[1])


def test_sixteen_bit_png():
    arr = (np.linspace(0, 65535, 300 * 300).reshape(300, 300)).astype(np.uint16)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, "PNG")
    img = load_image(buf.getvalue())
    assert img.gray.dtype == np.uint8
    assert img.gray.max() > 200 and img.gray.min() < 50


def test_corrupt_bytes_raise():
    with pytest.raises(ImageDecodeError):
        load_image(b"not an image at all")
    with pytest.raises(ImageDecodeError):
        load_image(b"")


def test_display_image_keeps_aspect():
    gray = np.zeros((1000, 800), np.uint8)
    out = make_display_image(gray, 512)
    assert out.shape == (512, 410)


def _make_dicom(tmp_path):
    pydicom = pytest.importorskip("pydicom")
    from pydicom.dataset import FileDataset, FileMetaDataset
    from pydicom.uid import ExplicitVRLittleEndian, generate_uid

    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.1"
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds = FileDataset(str(tmp_path / "x.dcm"), {}, file_meta=meta, preamble=b"\0" * 128)
    ds.PatientName = "Doe^Jane"
    ds.PatientID = "12345"
    ds.InstitutionName = "General Hospital"
    ds.Modality = "CR"
    ds.Rows, ds.Columns = 300, 260
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    ds.PixelData = (np.arange(300 * 260) % 4096).astype(np.uint16).tobytes()
    path = tmp_path / "x.dcm"
    ds.save_as(str(path), enforce_file_format=True)
    return pydicom, path


def test_dicom_decoding(tmp_path):
    _, path = _make_dicom(tmp_path)
    img = load_image(path.read_bytes(), "x.dcm")
    assert img.is_dicom and img.format == "DICOM"
    assert img.gray.shape == (300, 260) and img.gray.dtype == np.uint8


def test_strip_dicom_identifiers(tmp_path):
    pydicom, path = _make_dicom(tmp_path)
    ds = pydicom.dcmread(str(path))
    strip_dicom_identifiers(ds)
    assert "PatientName" not in ds and "PatientID" not in ds and "InstitutionName" not in ds
    assert ds.Modality == "CR"
