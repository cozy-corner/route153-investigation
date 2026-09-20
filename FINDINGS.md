# 都道153号線「自己交差」調査ドキュメント

## 背景

立川のテックイベント(Tachikawa.any #3、LT枠あり、「立川とわたし」に触れることが必須)向けのネタとして、「東京都道153号立川昭島線が、自分自身(153号)と交差している」という現象を調査した記録。

## 結論

**立川市内に、都道153号が都道153号と交差している地点が、少なくとも2箇所ある。**
いずれも座標の近似ではなく、OSM(OpenStreetMap)上で実際に**同一のノードIDを複数のwayが共有している**ことまで確認済み。市の行政境界を余裕を持ってカバーする範囲(139.34-139.46E, 35.67-35.76N)で再検索しても、この2箇所以外は見つかっていない。

### 確定した交差点1: 昭和記念公園立川口前(OSM上の正式名称)

- OSM上のノード名(`name`タグ): `昭和記念公園立川口前`(英語名: Showa Kinen Park Tachikawaguchi)
- 座標: `35.7017962, 139.4066669`
- 共有ノードID: `540037425`
- 構造: 東西方向の「立川昭島線」(way 323785942)が1本の連続したwayとしてこの点を素通りし、南北方向の「中央南北線」(way 323785929, 323785930)がちょうどこの点で終わる/始まる形で交差
- Google Maps: https://www.google.com/maps/@35.7017962,139.4066669,19z
- OSM直リンク:
  - https://www.openstreetmap.org/node/540037425
  - https://www.openstreetmap.org/node/190138057(同じく`昭和記念公園立川口前`)
  - https://www.openstreetmap.org/node/540037143(同上)
  - https://www.openstreetmap.org/node/534229690(同上)
  - (いずれも半径40m以内の同一交差点クラスタ)

### 確定した交差点2: 立川広域防災基地付近(OSM上に名前タグなし、周辺施設名から命名)

- OSM上のノードには`name`タグが無く(`highway=traffic_signals`のみ)、便宜上「立川広域防災基地付近」と呼んでいる
- 座標: `35.7105921, 139.386819`(クラスタ代表点)
- 共有ノードID: `4824540367`ほか、約11m圏内に3つの近接ノード(4824540378, 4824540377, 1398309945)
- 構造: 4方向(東西南北、それぞれ約90度刻み)すべてが独立したwayの端点として集まる、正真正銘の十字路。4本とも`ref=153`(立川昭島線)。
  - 489740168: 西方向(bearing ≈271°)
  - 490277657: 北方向(bearing ≈360°/0°)
  - 850514489: 南方向(bearing ≈182°)
  - 850514490: 東方向(bearing ≈96°)
- Google Maps: https://www.google.com/maps/@35.7105921,139.386819,19z
- OSM直リンク:
  - https://www.openstreetmap.org/node/4824540367
  - https://www.openstreetmap.org/node/4824540378
  - https://www.openstreetmap.org/node/4824540377
  - https://www.openstreetmap.org/node/1398309945

両クラスタに含まれる全wayについて、`ref`タグが例外なく`153`であることを直接確認済み。

## 検討して却下した地点

いずれもref=153の道が最大2本しか集まっておらず(次数2、単なる折れ曲がりや通過点)、交差ではなかった。

- **名前タグなしの交差点**(座標35.6998208, 139.4048749。OSM上に`name`タグ自体が存在しない): https://www.openstreetmap.org/node/912045478
  調査序盤でこのノードを誤って「昭和記念公園立川口前」と呼んでいたが、その名前は実際には交差点1(540037425)のものであり誤りだった。
- **昭和記念公園あけぼの口**(OSM上の名前。ref=153は最大でも2本):
  https://www.openstreetmap.org/node/540036869 /
  https://www.openstreetmap.org/node/540037427 /
  https://www.openstreetmap.org/node/540037577
- **立川北駅前**(OSM上の名前。ref=153は最大でも2本、いずれも同じ「立川昭島線」の通過区間):
  https://www.openstreetmap.org/node/540040528 /
  https://www.openstreetmap.org/node/540040529 /
  https://www.openstreetmap.org/node/540041083

## 使った手法

### 最終的に採用した方法: ノードID一致(確定した2つの交差点はこれで検出)

各wayが参照する**ノードIDのリスト**を見て、複数のwayが**同一のノードID**を共有しているかで交差を判定する。座標の近さは一切使わない。具体的な手順は下記「再現方法」の通りで、`scripts/selfcross.py` がこの方式を実装している。

この方式で見つけた交差点パターンは2種類あった:
- 1本の道が貫通way(その点を通過点として持つ)+ もう1本の道が両側から端点として突き刺さる(交差点1・昭和記念公園立川口前)
- 4本の道全てが端点として1点に集まる、貫通wayが無いパターン(交差点2・防災基地付近。方位角を計算し、東西南北にほぼ90度刻みで分かれていることを確認して本物と判定)
最初はこの1つ目のパターンだけを想定しており、2つ目のパターンは見落としかけた。**判定パターンを限定しすぎると見逃す**という教訓。

### 途中で試して捨てた方法: 座標の近似(153号の確定結論には使っていない)

関東全域・全ref番号への大規模スキャンを試みた際、各wayの座標(緯度経度)を使い「距離が閾値(8〜15m)以内なら同じ点とみなす」というロジックで交差点を探した(個別確認はOverpass APIの`around`検索、一括スキャンはローカルデータのGeoJSON化)。これは**OSMの本来のデータモデル(Node/Way/Relationのうち、Nodeが位置の一次情報)を無視した代用**であり、以下の問題が起きて放棄した:

- たまたま近い場所に存在するだけの無関係なway(同じ道路が重複してトレースされたもの等)まで「交差」と誤判定する
- `ref`タグは都道府県ごとに独立採番されているため、関東全域で同じref番号を集めると無関係な道路まで混ざる
- 片側複数車線の分離帯やトンネル/高架の分岐など、`ref`が同じ道同士が"触れる"ありふれたインフラ表現が大量にヒットする。実際にサンプル確認した3件(ref20・ref319・ref6)は全てハズレだった。うち2件(ref319=外苑東通り、ref6=江戸通り)はトンネル/高架の分岐と見られる。残る1件(ref20=野猿街道)は当初「一方通行ペア」と判断したが、後にノードID単位で見直したところ、実際には同じ道が重複して複数wayとして取り込まれているデータ品質の問題だったと判明した(角度や名前だけでの判断は誤りやすい)

この座標近似の方式で出た候補件数は、上記の欠陥のため信頼できる数値ではないので記載しない。153号の確定結論(交差点1・2)には一切使っていない。

## 再現方法

```bash
# 1. 立川市の行政境界を余裕を持ってカバーする範囲を、関東地方のOSM抽出データ
#    (~/y-junctions-data/osm/kanto-latest.osm.pbf)から切り出す
osmium extract --bbox 139.34,35.67,139.46,35.76 \
  ~/y-junctions-data/osm/kanto-latest.osm.pbf -o tachikawa_full_area.osm.pbf --overwrite -s smart

# 2. ref=153のwayだけを、参照ノードごと抽出
osmium tags-filter tachikawa_full_area.osm.pbf w/ref=153 \
  -o data/r153_tachikawa_full.osm.pbf --overwrite

# 3. ノードID・座標・タグを保持したまま OPL(テキスト)形式に変換
osmium cat data/r153_tachikawa_full.osm.pbf -f opl -o data/r153_tachikawa_full.opl --overwrite

# 4. ノードID一致で交差点を検出
python3 scripts/selfcross.py report data/r153_tachikawa_full.opl data/routes.opl /tmp/r153.json
```

現在リポジトリに残っているファイル:
- `data/r153_tachikawa_full.osm.pbf` / `data/r153_tachikawa_full.opl` — 立川市の行政境界を余裕を持ってカバーする範囲に絞ったデータ(上記コマンドの成果物。網羅性を確認した最終版)
- `scripts/selfcross.py` — ノードID一致による交差検出スクリプト。調査当時は find_153_crossing.py という153号専用スクリプトだったが、多摩地方への拡張時に全ref対応の `scripts/selfcross.py` へ統合し、専用スクリプトは削除した。同じ入力で検出結果が一致することを確認済み(8ノード: 190138057, 534229690, 540037143, 540037425, 1398309945, 4824540367, 4824540377, 4824540378)

## 参考資料

- 東京都道153号立川昭島線 - Wikipedia: https://ja.wikipedia.org/wiki/%E6%9D%B1%E4%BA%AC%E9%83%BD%E9%81%93153%E5%8F%B7%E7%AB%8B%E5%B7%9D%E6%98%AD%E5%B3%B6%E7%B7%9A
- 立川の道・交差点「都道153号立川昭島線・中央南北線」 | 多摩てばこネット: https://www.tamatebakonet.jp/town/detail/id=15650
- note記事(旧153号=八王子立川線からの付け替えの歴史、キロポスト現物の記録): https://note.com/kiloposter/n/n340dc6b63b52
- Tachikawa.any #3 (発表イベント): https://tachikawaany.connpass.com/event/406562/
