# 路線の自己交差 調査

「東京都道153号立川昭島線が、自分自身と交差している」という話から始まり、同じ現象が
どれくらいあるのかを多摩地方全域で調べた記録。立川のテックイベント Tachikawa.any #3 の
LTネタとして調査したもの。

データは OpenStreetMap。座標の近さではなく、**複数のwayが同一のノードIDを共有しているか**
で交差を判定している。

## ドキュメント

| | 内容 |
|---|---|
| **[FINDINGS.md](FINDINGS.md)** | 最初の調査。立川市 × 都道153号。確定した2交差点(昭和記念公園立川口前 / 立川広域防災基地付近)と、そこに至るまでに試して捨てた手法 |
| **[TAMA_FINDINGS.md](TAMA_FINDINGS.md)** | 多摩地方 × 国道・都道すべてに広げた調査。**現在の主結果**。候補58箇所のうち交差21箇所(埼玉分1件を除くと20箇所)。判定基準、アームの数え方、交差と分岐・合流の区別、未解決の問題、再現手順、全58件の表(交差点名・方位別の路線名つき) |

`TAMA_FINDINGS.md` の数字が最新。`FINDINGS.md` は153号に限った最初の記録で、
そこに書かれている2交差点は現在の実装でも同じ結果として再現される。

## スクリプト

**実装は `scripts/selfcross.py` の1本だけ。** 検出・分類・出力がすべてここに入っている。

```bash
# 検出して分類し、JSONと表を出す
python3 scripts/selfcross.py report <ref絞り込み済み.opl> <routes.opl> <out.json>
```

入力の作り方(`osmium` で関東の抽出データから切り出す手順)は `TAMA_FINDINGS.md` の
「再現方法」にある。

## データ

| | 内容 |
|---|---|
| `data/tama_ref.osm.pbf` | 多摩地方の `ref` 付き道路way。`report` の入力 |
| `data/tama_self_crossings.json` | 多摩58件の結果。構造判定・全way ID・ノードIDを含む |
| `data/r153_tachikawa_full.osm.pbf` / `.opl` | 立川市 × ref=153 のデータ(`FINDINGS.md` 用) |

元データ (`~/y-junctions-data/osm/kanto-latest.osm.pbf`) はこのリポジトリには入っていない。
中間ファイル(tama.osm.pbf、tama_ref.opl、routes.opl など)も置いていない。
どちらも再現手順のコマンドで生成できる。
