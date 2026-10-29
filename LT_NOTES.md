# LT カンペ

Tachikawa.any #3 のLT「同じ番号の道が、自分自身と交差している」の発表メモ(要点だけ)。スライドの各ページの発表メモ(スピーカーノート)と同じ内容。

- スライド: https://claude.ai/artifact/RUrHo3LV1VQbTXi1hdXXX7 (非公開。ほかの人に見せるには、ページの共有メニューで共有する)
- 各ページ先頭の【】は、発表開始からの経過時間(本編は6分(1枚1分)。最後のページはおまけ)。
- データ:多摩地方の国道・都道、OSM(2025年12月の関東抽出)。検出は scripts/selfcross.py、結果は TAMA_FINDINGS.md と data/tama_self_crossings.json。最新のOSMでの検出のやり直しは、まだ行っていない。
- 図の画像(OSMの画面、地理院地図にref=153の道を重ねた図)は、このリポジトリには入れていない。各ページの地図のURLは、そのページの項目に書いた。表紙の標識写真は data/route153.jpeg。
- 出典・OSMのタグの確認日は 2026-10-29。

## 1. 同じ番号の道が、自分自身と交差している

**【0:00〜1:00】**

- 自己紹介:[立川と153号]
- 写真の標識は、全方向が153号

## 2. 都道153号が、153号と交差している

**【1:00〜2:00】**

- 153号同士の交差が、立川市内に2箇所
- 左の地図: https://www.openstreetmap.org/node/4824540367
- 右の地図: https://www.openstreetmap.org/node/540037425

## 3. 都道153号は、立川と昭島をつなぐ

**【2:00〜3:00】**

- 起点は曙町二丁目、終点は朝日町三丁目。全長は約10.9km(Wikipedia)
- 北へ延びる中央南北線も153号(支線)
- 青線は玉川町二丁目まで。そこから終点までは昭島市道で、ref=153が付いていない
- 郷地町〜福島交番前の途切れ:ref=29だけ。実際は29号との重複区間(Wikipedia)
- 東中神の途切れ:ref=151
- 地図: https://maps.gsi.go.jp/#15/35.706/139.3966/

## 4. OpenStreetMap(OSM)は、みんなで作る地図

**【3:00〜4:00】**

- OSMのデータは誰でも使える(ODbL、出典表示が必要)
- wayが持つのは、ノードIDの並び(nd)とタグだけ。座標はノードが持つ
- XMLのnodeは、wayの最初のノード(APIの値。version等の属性は省略)
- 形式:APIはXML。今回使った関東の切り出しはPBF(同じ中身のバイナリ)
- 例のway: https://www.openstreetmap.org/way/323785942

## 5. ノードIDで確かめた

**【4:00〜5:00】**

- 立体交差はノードを共有しない(OSM Wiki「Key:layer」)。だからノードIDで数えれば、立体交差は入らない
- 左の図は、反対向きの車線を省いている
- 左の図の元: https://www.openstreetmap.org/node/540037425

## 6. 同じ番号の道の出会い方は、3パターン

**【5:00〜6:00】**

- 多摩全体で、同じ番号の道同士の交差は21箇所・16路線。153号だけの話ではない
- 旧道と新道の5件:元橋本、小野路、中河原駅北、乞田新大橋、宮沢(Wikipedia)
- 限界:機械で判定しただけで、現地は見ていない
- 限界:路線番号(ref)が付いた道しか数えていない
- 限界:60度の境目は私が決めた仮の値
- 限界:国道と都道の区別が不完全
- 限界:範囲が長方形なので、都外が1件混ざる(笹井)
- プラス型の地図: https://www.openstreetmap.org/node/4824540367
- 並行型の地図: https://www.openstreetmap.org/node/279807070
- Y型の地図: https://www.openstreetmap.org/node/3817661434

## 7. おまけ:玉川上水と残堀川の交差

**【おまけ 6:00〜7:00】**

- 今の立体交差になったのは1963年(Wikipedia「残堀川」)
- 玉川上水のwayのタグ:tunnel=yes、layer=-1
- 地図: https://www.openstreetmap.org/#map=18/35.72734/139.38766
- 玉川上水のway: https://www.openstreetmap.org/way/60964194
- 残堀川のway: https://www.openstreetmap.org/way/1117757672

## 参考にした資料

- 東京都道153号立川昭島線 - Wikipedia: https://ja.wikipedia.org/wiki/%E6%9D%B1%E4%BA%AC%E9%83%BD%E9%81%93153%E5%8F%B7%E7%AB%8B%E5%B7%9D%E6%98%AD%E5%B3%B6%E7%B7%9A
- 立川の道・交差点「都道153号立川昭島線・中央南北線」 | 多摩てばこネット: https://www.tamatebakonet.jp/town/detail/id=15650
- note(kiloposter、旧153号=八王子立川線からの付け替え。独自調査): https://note.com/kiloposter/n/n340dc6b63b52
- 残堀川 - Wikipedia(おまけ。玉川上水との立体交差、1963年に変更): https://ja.wikipedia.org/wiki/%E6%AE%8B%E5%A0%80%E5%B7%9D
- 地理院地図(3枚目の背景): https://maps.gsi.go.jp/
- OpenStreetMap(道路データ): © OpenStreetMap contributors。ライセンス(ODbL): https://www.openstreetmap.org/copyright
- OSM Wiki「Key:layer」(立体交差でノードを共有しない根拠): https://wiki.openstreetmap.org/wiki/Key:layer
- 削除したお知らせページの記事(Y字路を地図で探せるサービス): https://note.com/cozy_corner4321/n/n91147a760c68
