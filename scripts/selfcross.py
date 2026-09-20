"""
Detect routes that cross themselves, using real OSM node IDs (not coordinate proximity).

This is the whole implementation -- detection, classification and both output formats.
Run it with `report` to produce the result JSON and the Markdown table.
See the bottom of the file for usage.

Criterion:
    a node shared by >= 2 distinct ways carrying the same `ref`, whose total
    edge-degree at that node (interior = 2 edges, endpoint = 1) is >= 4,
    and whose arms point in at least 3 distinct compass directions.

The degree test alone comes from the 153 investigation in FINDINGS.md. It counts edges
and ignores direction, so wherever a route splits into two one-way carriageways or a
ramp rejoins it, four edge-ends of the same ref meet on a single axis and the point
qualifies without anything crossing. The direction test removes that class. Re-running
the 153 data with it still yields the two crossings recorded in FINDINGS.md.

Input is an OPL file produced from a PBF already clipped to an area and filtered to
highway ways carrying a `ref` tag (referenced nodes included).

Nothing here filters results out. Geometry checks classify each candidate instead --
the point of the survey is to find out how many such points exist, not to shrink the
list to a reviewable size.
"""
import json, math, re
from collections import Counter, defaultdict
import heapq

OPL_ESCAPE = re.compile(r"%([0-9a-fA-F]+)%")
SPIKE_TOL = 40.0      # edges this close in bearing mean a way doubles back on itself
REACH_LIMIT_M = 400.0  # how far to follow a ref before calling the arm long enough


# --------------------------------------------------------------------------- parsing

def unesc(s):
    return OPL_ESCAPE.sub(lambda m: chr(int(m.group(1), 16)), s)


def parse_opl(path):
    """-> ({node_id: (lat, lon)}, {way_id: {'node_ids': [...], 'tags': {...}}})"""
    nodes, ways = {}, {}
    with open(path) as f:
        for line in f:
            fields = line.rstrip("\n").split(" ")
            head = fields[0]
            if not head:
                continue
            if head[0] == "n":
                x = y = None
                for tok in fields[1:]:
                    if tok.startswith("x") and len(tok) > 1:
                        x = float(tok[1:])
                    elif tok.startswith("y") and len(tok) > 1:
                        y = float(tok[1:])
                if x is not None and y is not None:
                    nodes[int(head[1:])] = (y, x)
            elif head[0] == "w":
                node_ids, tags = [], {}
                for tok in fields[1:]:
                    if tok.startswith("N"):
                        node_ids = [int(v[1:]) for v in tok[1:].split(",") if v]
                    elif tok.startswith("T"):
                        for kv in tok[1:].split(","):
                            if "=" in kv:
                                k, v = kv.split("=", 1)
                                tags[unesc(k)] = unesc(v)
                ways[int(head[1:])] = {"node_ids": node_ids, "tags": tags}
    return nodes, ways


def node_names(path):
    """Intersection names live on the shared node itself (highway=traffic_signals + name)."""
    out = {}
    for line in open(path):
        if not line or line[0] != "n":
            continue
        fields = line.rstrip("\n").split(" ")
        for tok in fields[1:]:
            if tok.startswith("T") and len(tok) > 1:
                for kv in tok[1:].split(","):
                    if kv.startswith("name="):
                        out[int(fields[0][1:])] = unesc(kv[5:])
    return out


def refs_of(tags):
    """A way may carry several refs on an overlap section (ref=20;153)."""
    return [r.strip() for r in re.split(r"[;/]", tags.get("ref", "")) if r.strip()]


# -------------------------------------------------------------------------- geometry

def metres(a, b):
    return math.hypot((a[0] - b[0]) * 111320.0,
                      (a[1] - b[1]) * 111320.0 * math.cos(math.radians(a[0])))


def bearing(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    dlon = lon2 - lon1
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def angdiff(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def cluster_dirs(bearings, tol=45.0):
    """How many distinct compass directions the arms point in."""
    clusters = []
    for b in sorted(bearings):
        for c in clusters:
            if angdiff(b, c[0]) <= tol:
                c.append(b)
                break
        else:
            clusters.append([b])
    if len(clusters) > 1 and angdiff(clusters[0][0], clusters[-1][0]) <= tol:
        clusters[0].extend(clusters.pop())
    return len(clusters)


def through_axes(bearings, opposite_tol=35.0, axis_tol=40.0):
    """Directions the route runs straight through -- a pair of near-opposite arms."""
    axes, used = [], set()
    for i in range(len(bearings)):
        if i in used:
            continue
        for j in range(i + 1, len(bearings)):
            if j not in used and angdiff(angdiff(bearings[i], bearings[j]), 180) <= opposite_tol:
                axis = bearings[i] % 180
                if all(angdiff(axis * 2, a * 2) / 2 > axis_tol for a in axes):
                    axes.append(axis)
                used |= {i, j}
                break
    return axes


# ------------------------------------------------------------------------- detection

MIN_DIRS = 3  # fewer than three directions means the arms lie on one axis: not a junction


def candidates(nodes, ways):
    """Nodes where one ref reaches edge-degree 4 or more across two or more ways,
    with arms spread over at least MIN_DIRS directions."""
    by_ref = defaultdict(lambda: defaultdict(list))
    for wid, w in ways.items():
        nl = w["node_ids"]
        for r in refs_of(w["tags"]):
            for idx, nid in enumerate(nl):
                by_ref[r][nid].append((wid, "endpoint" if idx in (0, len(nl) - 1) else "interior"))

    out = []
    for ref, node_hits in by_ref.items():
        for nid, hits in node_hits.items():
            if len({w for w, _ in hits}) < 2 or nid not in nodes:
                continue
            degree = sum(2 if k == "interior" else 1 for _, k in hits)
            if degree < 4:
                continue
            bs = arm_bearings(nodes, ways, nid, {w for w, _ in hits})
            dirs = cluster_dirs(bs)
            if dirs < MIN_DIRS:
                continue
            out.append({"ref": ref, "node_id": nid, "coord": nodes[nid], "degree": degree,
                        "dirs": dirs, "axes": through_axes(bs),
                        "ways": sorted({w for w, _ in hits})})
    return out


def arm_bearings(nodes, ways, nid, wids, exclude=()):
    """Bearing of every edge leaving `nid`, skipping edges into `exclude`."""
    out = []
    for wid in wids:
        nl = ways[wid]["node_ids"]
        for i, n in enumerate(nl):
            if n != nid:
                continue
            for j in (i - 1, i + 1):
                if 0 <= j < len(nl) and nl[j] in nodes and nl[j] not in exclude:
                    out.append(bearing(nodes[nid], nodes[nl[j]]))
    return out


def cluster(cands, radius_m):
    """Group nearby same-ref candidates: a split carriageway crossroads is four nodes."""
    grouped = defaultdict(list)
    for c in cands:
        grouped[c["ref"]].append(c)
    out = []
    for ref, rs in grouped.items():
        pool = list(rs)
        while pool:
            group = [pool.pop()]
            changed = True
            while changed:
                changed = False
                for o in list(pool):
                    if any(metres(o["coord"], g["coord"]) <= radius_m for g in group):
                        pool.remove(o)
                        group.append(o)
                        changed = True
            out.append({"ref": ref, "nodes": group})
    return out


# -------------------------------------------------------------- structure and checks

SHORT_LINK_M = 40.0   # a link this short at a junction is usually internal to it
CONTINUE_CONE = 60.0  # how far off the arm's bearing the route may continue and still count


def _continues(nodes, ways, ref, nid, far, b0):
    """Does `ref` carry on past `far` in roughly the direction the arm points?"""
    for w in ways.values():
        if ref not in refs_of(w["tags"]):
            continue
        nl = w["node_ids"]
        if far not in nl:
            continue
        k = nl.index(far)
        for t in (k - 1, k + 1):
            if 0 <= t < len(nl) and nl[t] in nodes and nl[t] != nid:
                if angdiff(bearing(nodes[far], nodes[nl[t]]), b0) <= CONTINUE_CONE:
                    return True
    return False


def outward_arms(nodes, ways, ref, group, wids):
    """Arms the route really leaves the junction by.

    Two kinds of edge are not arms, and both otherwise turn a plain T junction into a
    four-way crossing:

    - links between the nodes of one intersection. Where a route is drawn as two one-way
      carriageways, a single real junction is several OSM nodes (both confirmed 153
      crossings are boxes of four), and the edges between them are internal.
    - short links whose ref does not carry on beyond them. At 瑞穂松原 the 9 m edge to the
      far carriageway of 青梅街道 read as a fourth arm, but 新青梅街道 only ever leaves to the
      southeast: the junction is a Y, not a crossing. Same at 明治通り x 永代通り, where the
      13 m median crossing carried `ref=10;306` while 明治通り south of it is `306` alone.
    """
    ids = {n["node_id"] for n in group}
    arms = []
    for nid in ids:
        for wid in wids:
            nl = ways[wid]["node_ids"]
            if nid not in nl:
                continue
            i = nl.index(nid)
            for j in (i - 1, i + 1):
                if not (0 <= j < len(nl)) or nl[j] not in nodes or nl[j] in ids:
                    continue
                far = nl[j]
                b0 = bearing(nodes[nid], nodes[far])
                if metres(nodes[nid], nodes[far]) <= SHORT_LINK_M \
                        and not _continues(nodes, ways, ref, nid, far, b0):
                    continue
                arms.append(b0)
    return arms


def classify(arms):
    """Tell a crossing from a mere merge.

    Degree >= 4 does not imply a crossing: where a route is split into two one-way
    carriageways, a plain Y junction already reaches degree 4. What separates the two is
    whether the arms form two distinct straight-through axes (the route runs in and out
    on both) or only one (the route runs through on one axis and a third arm joins it).
    """
    if not arms:
        return "判定不能"
    d, ax = cluster_dirs(arms), len(through_axes(arms))
    if ax >= 2 and d >= 4:
        return "交差"
    if ax >= 2:
        return "交差の疑い"
    return "分岐・合流" if d >= 3 else "並走"


def spikes(nodes, ways, group, wids):
    """Ways that double back on themselves at the shared node -- an OSM geometry error.

    Real case at node 274185306 (多摩ニュータウン通り): a node belonging to the northbound
    carriageway is also spliced into the southbound way, giving it an ~85 m spike. The
    road does not cross itself there; the two carriageways merely run parallel.
    """
    out = []
    for n in group:
        nid = n["node_id"]
        for wid in wids:
            nl = ways[wid]["node_ids"]
            if nid not in nl:
                continue
            i = nl.index(nid)
            if i in (0, len(nl) - 1) or nl[i - 1] not in nodes or nl[i + 1] not in nodes:
                continue
            a, b = bearing(nodes[nid], nodes[nl[i - 1]]), bearing(nodes[nid], nodes[nl[i + 1]])
            if angdiff(a, b) <= SPIKE_TOL:
                out.append({"node": nid, "way": wid, "angle": round(angdiff(a, b))})
    return out


def adjacency(ways, ref):
    adj = defaultdict(set)
    for w in ways.values():
        if ref not in refs_of(w["tags"]):
            continue
        nl = w["node_ids"]
        for a, b in zip(nl, nl[1:]):
            adj[a].add(b)
            adj[b].add(a)
    return adj


def min_arm_reach(nodes, ways, ref, group, adj_cache):
    """Shortest distance the ref actually extends down any arm of this intersection.

    Real case at 明治通り x 永代通り: the fourth arm carried `ref=10` only for the length of
    the median crossing. An arm whose ref dies within a few tens of metres is an
    over-scoped tag, not a leg of the route.
    """
    adj = adj_cache.setdefault(ref, adjacency(ways, ref))
    ids = {n["node_id"] for n in group}
    best = None
    for nid in ids:
        for nb in adj.get(nid, ()):
            if nb in ids or nb not in nodes:
                continue
            r = _reach(nodes, adj, nid, nb)
            best = r if best is None else min(best, r)
    return round(best, 1) if best is not None else None


def _reach(nodes, adj, start, first, limit=REACH_LIMIT_M):
    """Furthest distance reachable from `start` via neighbour `first`, never re-crossing start."""
    far = metres(nodes[start], nodes[first])
    seen, pq = {start, first}, [(-far, first)]
    while pq:
        negd, n = heapq.heappop(pq)
        d = -negd
        if d >= limit:
            return limit
        for m in adj.get(n, ()):
            if m in seen or m not in nodes:
                continue
            seen.add(m)
            nd = d + metres(nodes[n], nodes[m])
            far = max(far, nd)
            heapq.heappush(pq, (-nd, m))
    return far


# --------------------------------------------------------------------------- output

CLUSTER_M = 60.0
NON_ROAD = {"footway", "path", "cycleway", "pedestrian", "steps"}
NOT_BUILT = {"proposed", "construction"}
ORDER = {"交差": 0, "交差の疑い": 1, "分岐・合流": 2, "並走": 3, "データ誤り": 4, "判定不能": 5}


def load_route_networks(routes_opl):
    """way id -> route-relation `network` values, used to tell 国道 from 都道."""
    net = defaultdict(set)
    for line in open(routes_opl):
        fields = line.rstrip("\n").split(" ")
        if not fields[0] or fields[0][0] != "r":
            continue
        tags, members = {}, []
        for tok in fields[1:]:
            if tok.startswith("T"):
                for kv in tok[1:].split(","):
                    if "=" in kv:
                        k, v = kv.split("=", 1)
                        tags[unesc(k)] = unesc(v)
            elif tok.startswith("M"):
                members = [v for v in tok[1:].split(",") if v]
        if tags.get("network"):
            for m in members:
                if m[0] == "w":
                    net[int(m[1:].split("@", 1)[0])].add(tags["network"])
    return net


def flags_for(tagsets, networks, ref, nat_refs):
    """Observable facts about a cluster, for prioritising manual checking. Never a filter."""
    f = []
    classes = {t.get("highway", "?") for t in tagsets}
    names = {t.get("name", "") for t in tagsets} - {""}
    if classes & NON_ROAD:
        f.append("非車道way混在")
    if classes & NOT_BUILT:
        f.append("未供用way混在")
    if classes and all(c.endswith("_link") for c in classes):
        f.append("ランプのみ")
    if ref in nat_refs and any(not n.startswith("JP:national") for n in networks):
        f.append("国道/都道ref衝突の疑い")
    if any("旧" in n for n in names):
        f.append("旧道を含む")
    if any(any(k in n for k in ("支線", "側道", "連絡路", "地下道")) for n in names):
        f.append("支線/側道/連絡路を含む")
    return f


def cmd_report(opl_path, routes_opl, out_json):
    nodes, ways = parse_opl(opl_path)
    node_name_map = node_names(opl_path)
    net = load_route_networks(routes_opl)
    nat_refs = {r for wid, ns in net.items() if wid in ways
                and any(n.startswith("JP:national") for n in ns)
                for r in refs_of(ways[wid]["tags"])}

    cands = candidates(nodes, ways)
    adj_cache = {}
    out = []
    for c in cluster(cands, CLUSTER_M):
        ref, group = c["ref"], c["nodes"]
        wids = sorted({w for n in group for w in n["ways"]})
        tagsets = [ways[w]["tags"] for w in wids]
        networks = sorted({n for w in wids for n in net.get(w, ())})
        sp = spikes(nodes, ways, group, wids)
        # The verdict and the reported direction/axis counts must come from the same arms,
        # or a row can read "4 directions, 2 axes" while being classified 並走.
        arms = outward_arms(nodes, ways, ref, group, wids)
        # A verdict of 並走 means the arms landed on one axis only once the junction's
        # internal links were discounted -- not a junction at all. It is labelled, never
        # dropped: every candidate the detector produced stays in the output.
        structure = "データ誤り" if sp else classify(arms)
        out.append({
            "ref": ref,
            "structure": structure,
            "kind": "国道の可能性あり" if ref in nat_refs else "都道",
            "lat": round(sum(n["coord"][0] for n in group) / len(group), 7),
            "lon": round(sum(n["coord"][1] for n in group) / len(group), 7),
            "n_nodes": len(group),
            "max_degree": max(n["degree"] for n in group),
            "dirs": cluster_dirs(arms),
            "axes": len(through_axes(arms)),
            "arms": len(arms),
            "classes": sorted({t.get("highway", "?") for t in tagsets}),
            "networks": networks,
            "names": sorted({t.get("name", "") for t in tagsets} - {""}),
            "ways": wids,
            "node_ids": [n["node_id"] for n in group],
            "name": next((node_name_map[n["node_id"]] for n in group
                          if n["node_id"] in node_name_map), None),
            "axes_by_compass": axes_by_compass(nodes, ways, ref, group, wids),
            "flags": flags_for(tagsets, networks, ref, nat_refs),
            "min_arm_reach_m": min_arm_reach(nodes, ways, ref, group, adj_cache),
            "spikes": sp,
        })

    out.sort(key=lambda c: (ORDER[c["structure"]], -c["dirs"], -c["axes"], -c["n_nodes"],
                            int(c["ref"]) if c["ref"].isdigit() else 9999))
    json.dump(out, open(out_json, "w"), ensure_ascii=False, indent=1)

    sys.stderr.write(f"candidate nodes: {len(cands)}  ->  intersections: {len(out)}\n")
    for k, v in sorted(Counter(c["structure"] for c in out).items(), key=lambda x: ORDER[x[0]]):
        sys.stderr.write(f"  {k}: {v}\n")

    print("| # | 構造 | ref | 種別 | 交差点名 | 方位別の路線 | 座標 | ノード数 | アーム | 方向数 | 貫通軸 | 最短アーム | フラグ | OSM |")
    print("|---|------|-----|------|---------|-------------|------|---------|-------|-------|--------|-----------|--------|-----|")
    for i, c in enumerate(out, 1):
        flags = list(c["flags"]) + (["wayの折り返し(データ誤り)"] if c["spikes"] else [])
        print(f"| {i} | **{c['structure']}** | {c['ref']} | {c['kind']} | {c['name'] or '—'} | "
              f"{c['axes_by_compass'] or '—'} | {c['lat']:.5f}, {c['lon']:.5f} | "
              f"{c['n_nodes']} | {c['arms']} | {c['dirs']} | {c['axes']} | "
              f"{c['min_arm_reach_m'] if c['min_arm_reach_m'] is not None else '-'} | "
              f"{'、'.join(flags) or '—'} | "
              f"[node](https://www.openstreetmap.org/node/{c['node_ids'][0]}) "
              f"[map](https://www.openstreetmap.org/#map=19/{c['lat']:.5f}/{c['lon']:.5f}) |")


COMPASS = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]


def axes_by_compass(nodes, ways, ref, group, wids):
    """Which road runs in which direction, e.g. 東西:立川昭島線 / 北東南西:中央南北線.

    Uses the same arms the verdict is based on, so the description never disagrees with it.
    """
    ids = {n["node_id"] for n in group}
    groups = defaultdict(set)
    for nid in ids:
        for wid in wids:
            nl = ways[wid]["node_ids"]
            if nid not in nl:
                continue
            i = nl.index(nid)
            for j in (i - 1, i + 1):
                if not (0 <= j < len(nl)) or nl[j] not in nodes or nl[j] in ids:
                    continue
                far = nl[j]
                b = bearing(nodes[nid], nodes[far])
                if metres(nodes[nid], nodes[far]) <= SHORT_LINK_M \
                        and not _continues(nodes, ways, ref, nid, far, b):
                    continue
                groups[COMPASS[round(b / 45) % 8]].add(ways[wid]["tags"].get("name", "(無名)"))
    parts, seen = [], set()
    for d in COMPASS:
        if d in groups and d not in seen:
            opp = COMPASS[(COMPASS.index(d) + 4) % 8]
            if opp in groups:
                parts.append(f"{d}{opp}:{'・'.join(sorted(groups[d] | groups[opp]))}")
                seen |= {d, opp}
    for d in COMPASS:
        if d in groups and d not in seen:
            parts.append(f"{d}(対向なし):{'・'.join(sorted(groups[d]))}")
    return " / ".join(parts)


USAGE = """usage:
  python3 scripts/selfcross.py report <ref-filtered.opl> <routes.opl> <out.json>
      detect and classify every self-crossing; writes the JSON and prints the Markdown table
"""


if __name__ == "__main__":
    import sys
    cmd, rest = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ("", [])
    if cmd == "report":
        cmd_report(*rest)
    else:
        sys.exit(USAGE)
