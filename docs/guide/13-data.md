# Chapter 13 — The data: sources, download, labels, splits, collecting your own

[← Chapter 12](12-explainability-gradcam.md) · [README](../../README.md) · Next: [Chapter 14 →](14-training-pipeline.md)

A model is only as good as its data. This chapter lists every dataset we use, exactly how to get it
(automatically or by hand), how labels are created, how the data is split without cheating, and how
you could collect a dataset of your own — properly and ethically.

---

## 13.1 Overview

| Dataset                                             | Who / where                                                     | Patients          | What we use it for                                      | Licence                                      |
| --------------------------------------------------- | --------------------------------------------------------------- | ----------------- | ------------------------------------------------------- | -------------------------------------------- |
| **Kermany et al.** "Chest X-Ray Images (Pneumonia)" | Guangzhou Women and Children's Medical Center, China            | Children aged 1–5 | **Main training/test data** (Normal, Bacterial, Viral)  | CC BY 4.0                                    |
| **Cohen et al.** COVID-19 image data collection     | Many hospitals / publications, worldwide                        | Adults            | Adult viral & bacterial pneumonia (experiments)         | Per image — see its `license` column         |
| **Figure1** COVID-19 chest X-ray dataset            | Figure1 (medical image sharing platform)                        | Adults            | Adult COVID-19 (experiments)                            | See the repository                           |
| **Shenzhen** chest X-ray set                        | Shenzhen No.3 Hospital, via the US National Library of Medicine | Adults            | 326 adult **normal** X-rays (experiments)               | Public for research; cite Jaeger et al. 2014 |
| **Actualmed** COVID-19 chest X-ray dataset          | Actualmed (Spain)                                               | Adults            | **Unseen-hospital test only** (127 normal, 58 COVID-19) | See the repository                           |

The deployed models (Version 1) are trained **only on Kermany**. The adult datasets were used to
measure adult performance and for the Version 2 experiment ([Chapter 22](22-results-and-lessons.md)).

## 13.2 Download everything automatically

From the `training/` folder, with Python available:

```bash
cd training
python download_data.py --dry-run     # shows what it will do
python download_data.py kermany       # 1.2 GB — enough for the main models
python download_data.py               # everything (~5 GB): kermany, cohen, figure1, actualmed, shenzhen
```

It uses only official sources (no accounts needed), shows progress, and skips anything already
downloaded, so you can re-run it after an interruption. Git must be installed for the three GitHub
datasets. Result:

```
training/data/
├── raw/chest_xray/{train,test}/{NORMAL,PNEUMONIA}/*.jpeg     ← Kermany
└── external/
    ├── covid-chestxray-dataset/          ← Cohen (images/ + metadata.csv)
    ├── Figure1-COVID-chestxray-dataset/
    ├── Actualmed-COVID-chestxray-dataset/
    ├── shenzhen_normal/CHNCXR_xxxx_0.png  (326 files)
    └── shenzhen_normal.csv
```

## 13.3 Download by hand (if you prefer clicking)

1. **Kermany** — open https://data.mendeley.com/datasets/rscbjbr9sj/2 → download
   **ChestXRay2017.zip** (1.2 GB) → unzip it into `training/data/raw/` so that
   `training/data/raw/chest_xray/train/NORMAL/` exists.
   (A Kaggle copy, _paultimothymooney/chest-xray-pneumonia_, also works but needs a Kaggle account;
   it contains a duplicated nested folder and a tiny 16-image `val` folder — our scripts handle both.)
2. **Cohen, Figure1, Actualmed** — on each GitHub page click **Code → Download ZIP** and unzip into
   `training/data/external/`, keeping the folder names shown above:
   - https://github.com/ieee8023/covid-chestxray-dataset
   - https://github.com/agchung/Figure1-COVID-chestxray-dataset
   - https://github.com/agchung/Actualmed-COVID-chestxray-dataset
3. **Shenzhen normals** — the file list is at
   https://data.lhncbc.nlm.nih.gov/public/Tuberculosis-Chest-X-ray-Datasets/Shenzhen-Hospital-CXR-Set/CXR_png/index.html.
   Files ending in `_0.png` are **normal**, `_1.png` are tuberculosis (we do not use those). Easier:
   `python download_data.py shenzhen`.

## 13.4 How labels are created

Kermany stores images in `NORMAL` and `PNEUMONIA` folders, and encodes the pneumonia type in the
**file name**:

```
NORMAL/IM-0115-0001.jpeg              → NORMAL,    patient 115
PNEUMONIA/person1_bacteria_1.jpeg     → BACTERIAL, patient "person1"
PNEUMONIA/person1_virus_6.jpeg        → VIRAL,     patient "person1"
```

`training/prepare_data.py` reads these with regular expressions. The labels come from the original
study's expert graders (the dataset paper describes a tiered grading process by physicians).

For the adult sets (`training/prepare_adult.py`):

- **Cohen**: the `finding` column — `Pneumonia/Viral/...` (COVID-19, SARS, MERS, influenza, varicella,
  herpes) → VIRAL; `Pneumonia/Bacterial/...` (Streptococcus, Mycoplasma, Klebsiella, Legionella, ...) →
  BACTERIAL; `No Finding` → NORMAL. We **exclude** unspecified "Pneumonia", fungal, tuberculosis, lipoid,
  aspiration, lateral views and CT scans, and patients under 18.
- **Figure1 / Actualmed**: `COVID-19` → VIRAL, `No finding` → NORMAL; frontal views only.
- **Shenzhen**: all NORMAL.

## 13.5 Cleaning and splitting (without cheating)

`python prepare_data.py --data-root data/raw/chest_xray` does:

1. **Pools** the original train and test folders (the original 16-image validation folder is far too
   small to use).
2. **Removes exact duplicates** by content hash (MD5) — 32 duplicate files in this dataset — and
   ignores macOS `__MACOSX` junk folders.
3. **Groups by patient** and splits **70 / 15 / 15** with `StratifiedGroupKFold` (20 folds → 14 train,
   3 validation, 3 test): no patient appears in two splits, and each split has the same mix of classes.

Result (children): **5,824 images from 2,789 patients**.

| Split      | Normal | Bacterial | Viral | Total |
| ---------- | ------ | --------- | ----- | ----- |
| Train      | 1,114  | 1,940     | 1,047 | 4,101 |
| Validation | 238    | 393       | 213   | 844   |
| Test       | 227    | 427       | 225   | 879   |

It writes `training/data/splits.csv`:

```
path,label,patient_id,split
/…/PNEUMONIA/person1_bacteria_1.jpeg,BACTERIAL,p_person1,train
```

`python prepare_adult.py` adds the adult sources (each split 70/15/15 by patient, **per label**, so even
the 54 adult bacterial images get a fair test share) into `data/splits_combined.csv` (6,776 images,
with a `source` column), and writes `data/external/actualmed.csv` — the **unseen-hospital test set**
that is never used for training.

## 13.6 Collecting your own data (manually and ethically)

If you work with a hospital and want to build or extend a dataset:

1. **Approval first.** Get approval from the institution's **ethics committee / IRB** and data-protection
   officer _before_ collecting anything. Use images only with **informed consent** or under an approved
   waiver. Never use patient images found online or shared informally.
2. **Export and de-identify.** Export frontal (PA/AP) chest X-rays from the hospital's PACS as DICOM or
   PNG. Remove names, IDs, dates, hospital names and any burned-in text. (Our app strips DICOM identifier
   tags automatically — `strip_dicom_identifiers()` in `preprocessing.py` — but do it before images
   ever leave the hospital.) Replace patient IDs with random codes and keep the key separately.
3. **Label carefully.**
   - _Normal vs pneumonia_: a radiologist's report, ideally confirmed by a second reader.
   - _Bacterial vs viral_: X-ray appearance alone is unreliable — use **laboratory confirmation**
     (sputum or blood culture for bacteria; PCR or antigen tests for viruses) recorded in the clinical notes.
   - Record uncertainty ("indeterminate") rather than guessing.
4. **Collect both classes from the same places.** Normal and pneumonia images should come from the same
   hospitals, machines and time periods — otherwise the model learns the _source_ instead of the
   _disease_ (this exact mistake is analysed in [Chapter 22](22-results-and-lessons.md)).
5. **Organise** as a CSV the pipeline can read:

   ```
   path,label,patient_id,split,source
   /data/myhospital/0001.png,NORMAL,mh_0001,train,myhospital
   /data/myhospital/0002.png,VIRAL,mh_0002,test,myhospital
   ```

   Labels must be `NORMAL`, `BACTERIAL` or `VIRAL`. Assign `split` by patient (you can copy the
   approach in `prepare_adult.py`). Then train with `--splits path/to/your.csv`.

6. **Or keep it for testing only.** For external validation (Stage 1) a simpler CSV is enough:

   ```
   path,label
   /data/myhospital/0001.png,0      ← 0 = normal, 1 = pneumonia
   ```

   `python external_validate.py --name "My hospital" --csv that.csv` — the fairest test of all.

## 13.7 Data for the input validator (optional)

The "is this a chest X-ray?" check currently uses rules (Chapter 16). To train a learned validator
(`training/train_validator.py`), create:

```
training/data/validator/
├── cxr/      thousands of frontal chest X-rays (e.g. a sample of the datasets above)
└── other/    everything else: natural photos (e.g. COCO/Open Images), documents & screenshots,
              other X-ray body parts (e.g. the MURA dataset — free registration), CT slices
```

## 13.8 Bigger datasets for the future

| Dataset                            | Size                   | Labels                                          | Access                                    |
| ---------------------------------- | ---------------------- | ----------------------------------------------- | ----------------------------------------- |
| RSNA Pneumonia Detection Challenge | ~26,700 adult CXRs     | Pneumonia / not (with boxes)                    | Free Kaggle account                       |
| NIH ChestX-ray14                   | 112,120 CXRs           | 14 findings incl. pneumonia (text-mined, noisy) | Free download (NIH Box)                   |
| CheXpert (Stanford)                | 224,316 CXRs           | 14 findings                                     | Free registration                         |
| MIMIC-CXR (MIT)                    | 377,110 CXRs + reports | Findings from reports                           | PhysioNet credentialing + training course |
| PadChest (Spain)                   | 160,000 CXRs           | 174 findings                                    | Free registration                         |

None of these provide reliable _bacterial vs viral_ labels at scale, which is the hardest part of this task.

---

Next: **Chapter 14 — The training pipeline: from images to models** → [14-training-pipeline.md](14-training-pipeline.md)
