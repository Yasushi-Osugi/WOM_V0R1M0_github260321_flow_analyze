# iPhone Demo Dataset README

## 1. このREADMEの目的

このドキュメントは、WOM demo で使用している **iPhone new model の Global Supply Chain dataset** について、  
以下の4層で構造を整理し、今後の保守・再生成・精度向上をしやすくすることを目的とします。 :contentReference[oaicite:0]{index=0}

- 原データ層
- 変換ロジック層
- WOM入力層
- `v0_1 → v0_2_regenerated → v0_3` の差分

本datasetは、単なるサンプルCSVではなく、**iPhone新モデルのグローバル供給網を題材にした demo / planning / visualization 用の proxy dataset** です。  
WOM上で、E2E network、global map、PSI、cashflow を一貫して見せることを狙っています。 

---

## 2. 全体像

本datasetは、次の流れで構成されています。

```text
iphone_proxy_dataset_v0_1
    ↓
map_iphone_proxy_to_wom_csv.py などの変換ロジック
    ↓
iphone_wom_mapped_v0_1
    ↓
iphone_wom_mapped_v0_2_regenerated
    ↓
iphone_wom_mapped_v0_3
    ↓
data/ 直下の最新WOM入力CSV