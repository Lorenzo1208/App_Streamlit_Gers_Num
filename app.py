import streamlit as st
import geopandas as gpd
import folium
from folium import GeoJson, GeoJsonTooltip
from streamlit_folium import st_folium
import pandas as pd
import os
import plotly.express as px

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="SIG RODP – Gers Numérique",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700;900&family=JetBrains+Mono:wght@400;600&display=swap');
* { font-family: 'DM Sans', sans-serif !important; }
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: #0a0e1a !important; color: #e8edf5 !important;
}
[data-testid="stSidebar"] {
    background: #0d1220 !important;
    border-right: 1px solid #1e2d4a !important;
}
[data-testid="stSidebar"] * { color: #c8d4e8 !important; }
[data-testid="stSidebarContent"] { padding: 1.5rem 1rem; }
.block-container { padding: 1rem 1.5rem !important; max-width: 100% !important; }
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 16px; }
.kpi-card {
    background: linear-gradient(135deg, #111827 0%, #0d1a2e 100%);
    border: 1px solid #1e3a5f; border-radius: 12px; padding: 16px 20px;
    position: relative; overflow: hidden;
}
.kpi-card::before { content:''; position:absolute; top:0; left:0; right:0; height:3px; background:linear-gradient(90deg,#0066cc,#00c4ff); }
.kpi-card.pub::before   { background: linear-gradient(90deg, #0066cc, #00c4ff); }
.kpi-card.priv::before  { background: linear-gradient(90deg, #e85d04, #ff9500); }
.kpi-card.total::before { background: linear-gradient(90deg, #6e40c9, #a78bfa); }
.kpi-card.km::before    { background: linear-gradient(90deg, #059669, #34d399); }
.kpi-label { font-size:10px; font-weight:700; letter-spacing:0.12em; text-transform:uppercase; color:#5a7fa8; margin-bottom:6px; }
.kpi-value { font-size:26px; font-weight:900; font-family:'JetBrains Mono',monospace !important; line-height:1; }
.kpi-value.pub   { color: #5bc4ff; }
.kpi-value.priv  { color: #ffaa4a; }
.kpi-value.total { color: #c4b5fd; }
.kpi-value.km    { color: #6ee7b7; }
.kpi-sub { font-size:11px; color:#3d6e9e; margin-top:3px; }
.section-title {
    font-size:10px; font-weight:700; letter-spacing:0.15em; text-transform:uppercase;
    color:#3d6e9e; margin:18px 0 8px 0; padding-bottom:6px; border-bottom:1px solid #1a2a3e;
}
.header-banner {
    background: linear-gradient(135deg, #0a1628 0%, #0d2145 50%, #0a1628 100%);
    border: 1px solid #1e3a5f; border-radius: 14px;
    padding: 18px 26px; margin-bottom: 14px;
    display: flex; align-items: center; justify-content: space-between;
}
.header-title { font-size:20px; font-weight:900; color:#ffffff; }
.header-sub   { font-size:12px; color:#5a8ab8; margin-top:3px; }
.header-badge { background:linear-gradient(135deg,#0066cc,#0044aa); color:white;
    padding:6px 14px; border-radius:20px; font-size:11px; font-weight:700; }
.legend-item { display:flex; align-items:center; gap:8px; margin-bottom:5px; font-size:11px; }
.legend-dot  { width:10px; height:10px; border-radius:50%; flex-shrink:0; }
[data-testid="stTabs"] button { color:#5a8ab8 !important; font-size:12px !important; font-weight:600 !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color:#5bc4ff !important; border-bottom-color:#5bc4ff !important; }
#MainMenu, footer { visibility:hidden; }
[data-testid="stToolbar"]   { display:none !important; }
[data-testid="stHeader"]    { background:transparent !important; }
[data-testid="stDecoration"]{ display:none !important; }
[data-testid="stSidebarCollapseButton"] { display:none !important; }
section[data-testid="stSidebar"] > div:first-child { padding-top: 1rem !important; }
::-webkit-scrollbar { width:5px; } ::-webkit-scrollbar-track { background:#0a0e1a; }
::-webkit-scrollbar-thumb { background:#1e3a5f; border-radius:3px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# COULEURS SUPPORTS (forme avec et sans accents)
# ─────────────────────────────────────────────
SUPPORT_COLORS = {
    # ── Souterrain ─────────────────────────────
    "Souterrain RIP construit":    "#00aaff",
    "Souterrain RIP Construit":    "#00aaff",   # variante casse
    "Souterrain RIP RAF":          "#0066cc",
    "Souterrain Orange":           "#9966ff",
    "Souterrain Tiers":            "#cc99ff",
    # ── Aérien ─────────────────────────────────
    "Aérien Enedis":               "#ffaa00",
    "Aerien Enedis":               "#ffaa00",
    "Aérien Orange":               "#ff7700",
    "Aerien Orange":               "#ff7700",
    "Aérien RIP":                  "#ffdd00",
    "Aerien RIP":                  "#ffdd00",
    # ── Aéro-souterrain ────────────────────────
    "Aéro-souterrain":             "#ff44aa",
    "Aero-souterrain":             "#ff44aa",
    "Aero-souterrain RIP":         "#ff44aa",
    "Aéro-souterrain Orange":      "#cc44aa",
    "Aero-souterrain Orange":      "#cc44aa",
    "Aero-souterrain Tiers":       "#dd77cc",   # nouveau type
    # ── Autres ─────────────────────────────────
    "Chambre":                     "#66ccff",
    "Façade":                      "#44ff88",
    "Facade":                      "#44ff88",   # sans cédille
    "Réseau en parcelle agricole": "#ff4444",
    "sans_tag":                    "#888888",
}
_color_lookup = {k.lower(): v for k, v in SUPPORT_COLORS.items()}

def get_color(val, fallback="#aaaaaa"):
    return _color_lookup.get(str(val).strip().lower(), fallback) if val else fallback

# ─────────────────────────────────────────────
# DOSSIER DONNÉES (classif cadastre)
# ─────────────────────────────────────────────
CLASSIF_DIR = os.environ.get(
    "SIG_CLASSIF_DIR",
    os.path.join("classif cadastre", "classif cadastre")
)

# ─────────────────────────────────────────────
# PRÉPARATION GDF
# ─────────────────────────────────────────────
def _prepare(gdf, extra_cols=None):
    """Nettoie les types, simplifie les géométries, réduit aux colonnes utiles."""
    g = gdf.copy()
    LENGTH_CANDIDATES = ["longueur", "cm_long", "LONGUEUR", "Shape_Leng", "shape_leng",
                         "Shape_Length", "shape_length", "longueur_m", "LONGUEUR_M", "len", "LEN"]
    if "longueur" not in g.columns:
        for cand in LENGTH_CANDIDATES:
            if cand in g.columns:
                g = g.rename(columns={cand: "longueur"})
                break
    col_map = {}
    for col in g.columns:
        cl = col.lower()
        if cl in ("domaine", "cm_support", "commune") and col != cl:
            col_map[col] = cl
    if col_map:
        g = g.rename(columns=col_map)

    useful = ["geometry", "domaine", "cm_support", "longueur", "commune",
              "cm_code", "type_class", "zanro", "zapm"]
    if extra_cols:
        useful += extra_cols
    g = g[[c for c in useful if c in g.columns]].copy()

    for col in g.columns:
        if col == "geometry":
            continue
        try:
            if pd.api.types.is_datetime64_any_dtype(g[col]):
                g[col] = g[col].astype(str)
            elif g[col].dtype == object:
                g[col] = g[col].apply(
                    lambda x: str(x) if not isinstance(x, (str, int, float, bool, type(None))) else x)
            else:
                g[col] = g[col].where(pd.notna(g[col]), None)
        except Exception:
            g[col] = g[col].astype(str)

    g["geometry"] = g["geometry"].simplify(0.00005, preserve_topology=True)
    return g


def _prepare_cadastre(gdf):
    """Prépare la couche cadastrale (polygones)."""
    g = gdf.copy()
    useful = ["geometry", "commune", "section", "numero", "contenance"]
    g = g[[c for c in useful if c in g.columns]].copy()
    for col in g.columns:
        if col == "geometry":
            continue
        try:
            if pd.api.types.is_datetime64_any_dtype(g[col]):
                g[col] = g[col].astype(str)
            elif g[col].dtype == object:
                g[col] = g[col].astype(str)
        except Exception:
            g[col] = g[col].astype(str)
    # Simplification plus forte pour les polygones (affichage navigateur)
    g["geometry"] = g["geometry"].simplify(0.0001, preserve_topology=True)
    return g


def _norm_df(df):
    LENGTH_CANDS = ["longueur", "cm_long", "LONGUEUR", "Shape_Leng", "shape_leng",
                    "Shape_Length", "shape_length", "longueur_m", "LONGUEUR_M", "len", "LEN"]
    if "longueur" not in df.columns:
        for c in LENGTH_CANDS:
            if c in df.columns:
                df = df.rename(columns={c: "longueur"})
                break
    col_map = {c: c.lower() for c in df.columns
               if c.lower() in ("domaine", "cm_support", "commune") and c != c.lower()}
    if col_map:
        df = df.rename(columns=col_map)
    for col in df.columns:
        try:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].astype(str)
        except Exception:
            pass
    return df


# ─────────────────────────────────────────────
# CHARGEMENT (mis en cache)
# ─────────────────────────────────────────────
@st.cache_data(show_spinner="Chargement et préparation des données…")
def load_all():
    """
    Scanne CLASSIF_DIR pour des dossiers "Commune <nom>/" contenant
    des sous-dossiers prive/ et public/ avec des shapefiles.
    Charge aussi couche cadastre/parcelles.shp filtré sur les communes trouvées.
    """
    import glob, re

    pub_frames  = []
    priv_frames = []
    commune_codes_found = set()   # codes INSEE extraits des zapm

    # ── Scanner les dossiers communes (déduplication casse Windows) ──────
    # On cherche "Commune *" dans CLASSIF_DIR ET dans la racine du projet
    SCAN_ROOTS = [CLASSIF_DIR, "."]
    _seen_dirs = set()
    _raw_dirs  = []
    for root in SCAN_ROOTS:
        for pattern in ("Commune *", "commune *", "COMMUNE *"):
            _raw_dirs += glob.glob(os.path.join(root, pattern))

    commune_dirs = []
    for d in _raw_dirs:
        k = os.path.normcase(os.path.abspath(d))
        if k not in _seen_dirs:
            _seen_dirs.add(k)
            commune_dirs.append(d)

    for commune_dir in commune_dirs:
        # Nom de commune depuis le nom du dossier
        basename = os.path.basename(commune_dir)
        commune_name = re.sub(r'^[Cc][Oo][Mm][Mm][Uu][Nn][Ee]\s+', '', basename).strip().title()

        # ── Tronçons privés ──────────────────────────────────────────────
        priv_shps = _dedup_shp(
            glob.glob(os.path.join(commune_dir, "prive",  "*.shp")) +
            glob.glob(os.path.join(commune_dir, "prive",  "*.SHP")) +
            glob.glob(os.path.join(commune_dir, "Prive",  "*.shp")) +
            glob.glob(os.path.join(commune_dir, "Privé",  "*.shp"))
        )
        for shp in priv_shps:
            g = _load_shp(shp, "Privé", commune_name)
            if g is not None:
                priv_frames.append(g)
                commune_codes_found |= _extract_insee(g)

        # ── Tronçons publics ─────────────────────────────────────────────
        pub_shps = _dedup_shp(
            glob.glob(os.path.join(commune_dir, "public", "*.shp")) +
            glob.glob(os.path.join(commune_dir, "public", "*.SHP")) +
            glob.glob(os.path.join(commune_dir, "Public", "*.shp"))
        )
        for shp in pub_shps:
            g = _load_shp(shp, "Public", commune_name)
            if g is not None:
                pub_frames.append(g)
                commune_codes_found |= _extract_insee(g)

    # ── Couche cadastrale ─────────────────────────────────────────────────
    cadastre_gdf = None
    cad_path = os.path.join(CLASSIF_DIR, "couche cadastre", "parcelles.shp")
    if os.path.exists(cad_path) and commune_codes_found:
        try:
            codes_sql = ",".join(f"'{c}'" for c in commune_codes_found)
            cadastre_gdf = gpd.read_file(cad_path, where=f"commune IN ({codes_sql})")
            if len(cadastre_gdf) > 0 and cadastre_gdf.crs and cadastre_gdf.crs.to_epsg() != 4326:
                cadastre_gdf = cadastre_gdf.to_crs(epsg=4326)
        except Exception as e:
            st.warning(f"Couche cadastrale : {e}")

    # ── Fusionner public + privé ──────────────────────────────────────────
    pub_gdf  = _merge_frames(pub_frames)
    priv_gdf = _merge_frames(priv_frames)

    gdfs = {
        "pub_voiries":  pub_gdf,
        "priv_voiries": priv_gdf,
        "cadastre":     cadastre_gdf,
    }
    gjs, dfs = {}, {}
    for key, gdf in gdfs.items():
        if gdf is not None and len(gdf) > 0:
            prep = _prepare_cadastre(gdf) if key == "cadastre" else _prepare(gdf)
            gjs[key] = prep.__geo_interface__
            df = gdf.drop(columns="geometry", errors="ignore").copy()
            dfs[key] = _norm_df(df)
        else:
            gjs[key] = None
            dfs[key] = pd.DataFrame()

    return gdfs, gjs, dfs


def _dedup_shp(paths):
    seen, out = set(), []
    for p in paths:
        k = os.path.normcase(p)
        if k not in seen:
            seen.add(k)
            out.append(p)
    return out


def _load_shp(path, default_domaine, commune_name):
    try:
        g = gpd.read_file(path)
        if len(g) == 0:
            return None
        # Calculer la longueur réelle depuis la géométrie en Lambert-93
        # AVANT la reprojection — c'est la valeur correcte pour la RODP
        # (cm_long hérite de la longueur du tronçon parent avant découpe cadastrale → incorrect)
        if g.crs and g.crs.to_epsg() == 2154:
            g["longueur"] = g.geometry.length.round(2)
        elif g.crs:
            g["longueur"] = g.to_crs(epsg=2154).geometry.length.round(2)
        else:
            g["longueur"] = g.geometry.length.round(2)
        # Reprojeter pour l'affichage
        if g.crs and g.crs.to_epsg() != 4326:
            g = g.to_crs(epsg=4326)
        # Injecter domaine et commune si absents
        if "domaine" not in g.columns:
            g["domaine"] = default_domaine
        if "commune" not in g.columns:
            g["commune"] = commune_name
        return g
    except Exception as e:
        st.warning(f"Impossible de charger {os.path.basename(path)}: {e}")
        return None


def _extract_insee(gdf):
    """Extrait les codes INSEE depuis la colonne zapm (ex: '32410/QLB/PMZ/...')."""
    codes = set()
    if "zapm" in gdf.columns:
        extracted = gdf["zapm"].dropna().str.split("/").str[0].str.strip()
        codes = set(extracted[extracted.str.len() == 5].unique())
    return codes


def _merge_frames(frames):
    if not frames:
        return None
    return gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs="EPSG:4326")


# ─────────────────────────────────────────────
# MODE DÉMO (si aucune donnée trouvée)
# ─────────────────────────────────────────────
def _demo():
    import numpy as np
    from shapely.geometry import LineString
    rng = np.random.default_rng(42)
    blon, blat = 0.9258, 43.7537
    def rl(n=5):
        return LineString(zip(blon + rng.uniform(-0.05, 0.05, n).cumsum() * 0.01,
                              blat + rng.uniform(-0.05, 0.05, n).cumsum() * 0.01))
    sp = ["Souterrain RIP construit", "Souterrain RIP RAF", "Aerien Enedis", "Aerien Orange"]
    sv = ["Façade", "Réseau en parcelle agricole", "Souterrain Orange", "Aero-souterrain RIP"]
    villes = ["Samatan"]
    pub  = gpd.GeoDataFrame([{"geometry": rl(), "domaine": "Public",
        "cm_support": rng.choice(sp), "longueur": round(rng.uniform(50, 500), 2),
        "commune": rng.choice(villes)} for _ in range(350)], crs="EPSG:4326")
    priv = gpd.GeoDataFrame([{"geometry": rl(), "domaine": "Privé",
        "cm_support": rng.choice(sv), "longueur": round(rng.uniform(30, 300), 2),
        "commune": rng.choice(villes)} for _ in range(200)], crs="EPSG:4326")
    gdfs = {"pub_voiries": pub, "priv_voiries": priv, "cadastre": None}
    gjs, dfs = {}, {}
    for k, g in gdfs.items():
        if g is not None:
            gjs[k]  = _prepare(g).__geo_interface__
            dfs[k]  = g.drop(columns="geometry")
        else:
            gjs[k], dfs[k] = None, pd.DataFrame()
    return gdfs, gjs, dfs


# ─────────────────────────────────────────────
# CHARGEMENT
# ─────────────────────────────────────────────
gdfs, gjs, dfs = load_all()
demo_mode = all(v is None or len(v) == 0 for v in gdfs.values())
if demo_mode:
    gdfs, gjs, dfs = _demo()

all_df = pd.concat([dfs.get("pub_voiries",  pd.DataFrame()),
                    dfs.get("priv_voiries", pd.DataFrame())], ignore_index=True)

# ─────────────────────────────────────────────
# FILTRAGE RAPIDE
# ─────────────────────────────────────────────
def fast_filter_gj(gj, show, sel_dom, sel_sup, sel_commune):
    if not show or not gj:
        return None
    dom_set = set(sel_dom)
    sup_set = set(sel_sup)
    feats = []
    for f in gj["features"]:
        p = f["properties"]
        if dom_set and "domaine" in p and p["domaine"] not in dom_set:
            continue
        if sup_set and "cm_support" in p and p["cm_support"] not in sup_set:
            continue
        if sel_commune and "commune" in p and p["commune"] not in set(sel_commune):
            continue
        feats.append(f)
    return {"type": "FeatureCollection", "features": feats} if feats else None


def fast_filter_df(df, show, sel_dom, sel_sup, sel_commune):
    if not show or df is None or len(df) == 0:
        return pd.DataFrame()
    d = df
    if "domaine"    in d.columns and sel_dom:    d = d[d["domaine"].isin(sel_dom)]
    if "cm_support" in d.columns and sel_sup:    d = d[d["cm_support"].isin(sel_sup)]
    if sel_commune  and "commune" in d.columns:  d = d[d["commune"].isin(sel_commune)]
    return d.reset_index(drop=True)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center;margin-bottom:20px;'>
        <div style='font-size:22px;'></div>
        <div style='font-size:14px;font-weight:900;color:#5bc4ff;'>SIG RODP</div>
        <div style='font-size:9px;color:#3d6e9e;letter-spacing:.1em;text-transform:uppercase;'>Gers Numérique</div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-title">Couches</div>', unsafe_allow_html=True)
    show_pub  = st.checkbox("Voiries publiques",  value=True)
    show_priv = st.checkbox("Voiries privées",    value=True)
    show_cad  = st.checkbox("Couche cadastrale",  value=False)

    st.markdown('<div class="section-title">Domaine</div>', unsafe_allow_html=True)
    sel_dom = st.multiselect("Domaine", ["Public", "Privé"], default=["Public", "Privé"])

    st.markdown('<div class="section-title">Type de support</div>', unsafe_allow_html=True)
    all_sup = sorted(all_df["cm_support"].dropna().unique().tolist()) if "cm_support" in all_df.columns else list(SUPPORT_COLORS)
    sel_sup = st.multiselect("Support réseau", all_sup, default=all_sup, placeholder="Tous…")
    if not sel_sup:
        sel_sup = all_sup

    st.markdown('<div class="section-title">Commune</div>', unsafe_allow_html=True)
    communes = sorted(all_df["commune"].dropna().unique().tolist()) if "commune" in all_df.columns else []
    sel_commune = st.multiselect("Commune", communes, default=communes, placeholder="Toutes…")
    if not sel_commune:
        sel_commune = communes

    st.markdown('<div class="section-title">Légende supports</div>', unsafe_allow_html=True)
    # Afficher uniquement les supports présents dans les données
    sup_displayed = all_sup if all_sup else list(SUPPORT_COLORS)
    for name in sup_displayed:
        color = SUPPORT_COLORS.get(name, "#888888")
        st.markdown(f'<div class="legend-item"><div class="legend-dot" style="background:{color};"></div>'
                    f'<span style="color:#9bb5cf;">{name}</span></div>', unsafe_allow_html=True)

    # ── Infos de chargement ──────────────────────────────────────────────
    st.markdown('<div class="section-title">Données chargées</div>', unsafe_allow_html=True)

    def _info(key, label, color):
        gdf = gdfs.get(key)
        df  = dfs.get(key, pd.DataFrame())
        if gdf is not None and len(gdf) > 0:
            n = len(gdf)
            communes_found = sorted(df["commune"].dropna().unique().tolist()) if "commune" in df.columns else []
            comm_str = ", ".join(communes_found) if communes_found else "-"
            # Méthode de classification
            tc_str = ""
            if "type_class" in df.columns:
                tc_vals = df["type_class"].dropna().unique()
                if len(tc_vals) > 0:
                    tc_str = f'<br><span style="color:#2a5a8e;font-style:italic;">{tc_vals[0]}</span>'
            st.markdown(
                f'''<div style="background:#0d1a2e;border:1px solid {color}33;border-left:3px solid {color};
                border-radius:6px;padding:8px 10px;margin-bottom:6px;font-size:11px;">
                <span style="color:{color};font-weight:700;">{label}</span>
                <span style="color:#5a7fa8;"> · {n:,} tronçons</span><br>
                <span style="color:#3d6e9e;">{comm_str}</span>{tc_str}
                </div>''', unsafe_allow_html=True)
        else:
            st.markdown(
                f'''<div style="background:#1a0d0d;border:1px solid #3a1e1e;border-left:3px solid #553333;
                border-radius:6px;padding:8px 10px;margin-bottom:6px;font-size:11px;">
                <span style="color:#664444;font-weight:700;">{label}</span>
                <span style="color:#443333;"> · non chargé</span>
                </div>''', unsafe_allow_html=True)

    _info("pub_voiries",  " Public", "#00aaff")
    _info("priv_voiries", " Privé",  "#ff8800")

    gdf_cad = gdfs.get("cadastre")
    if gdf_cad is not None and len(gdf_cad) > 0:
        st.markdown(f'''<div style="background:#0d1a2e;border:1px solid #44ff8833;border-left:3px solid #44ff88;
            border-radius:6px;padding:8px 10px;margin-bottom:6px;font-size:11px;">
            <span style="color:#44ff88;font-weight:700;"> Cadastre</span>
            <span style="color:#5a7fa8;"> · {len(gdf_cad):,} parcelles</span>
            </div>''', unsafe_allow_html=True)
    else:
        st.markdown('''<div style="background:#1a0d0d;border:1px solid #3a1e1e;border-left:3px solid #553333;
            border-radius:6px;padding:8px 10px;margin-bottom:6px;font-size:11px;">
            <span style="color:#664444;font-weight:700;"> Cadastre</span>
            <span style="color:#443333;"> · non chargé</span>
            </div>''', unsafe_allow_html=True)

    if demo_mode:
        st.markdown('<div style="margin-top:16px;background:#1a1a0d;border:1px solid #333300;'
                    'border-radius:8px;padding:10px;font-size:11px;color:#aaa830;">'
                    ' Mode démo</div>', unsafe_allow_html=True)




# ─────────────────────────────────────────────
# FILTRES
# ─────────────────────────────────────────────
fj_pub  = fast_filter_gj(gjs.get("pub_voiries"),  show_pub,  sel_dom, sel_sup, sel_commune)
fj_priv = fast_filter_gj(gjs.get("priv_voiries"), show_priv, sel_dom, sel_sup, sel_commune)
fj_cad  = gjs.get("cadastre") if show_cad else None   # pas de filtre supplémentaire sur cadastre

fd_pub  = fast_filter_df(dfs.get("pub_voiries"),  show_pub,  sel_dom, sel_sup, sel_commune)
fd_priv = fast_filter_df(dfs.get("priv_voiries"), show_priv, sel_dom, sel_sup, sel_commune)

# ─────────────────────────────────────────────
# MÉTRIQUES
# ─────────────────────────────────────────────
n_pub   = len(fj_pub["features"])  if fj_pub  else 0
n_priv  = len(fj_priv["features"]) if fj_priv else 0
n_total = n_pub + n_priv


def _sum_length(df):
    if df is not None and len(df) > 0 and "longueur" in df.columns:
        return pd.to_numeric(df["longueur"], errors="coerce").sum()
    return 0.0


km_pub  = _sum_length(fd_pub)
km_priv = _sum_length(fd_priv)

# ─────────────────────────────────────────────
# HEADER + KPIs
# ─────────────────────────────────────────────
st.markdown("""
<div class="header-banner">
    <div>
        <div class="header-title">Classification RODP – Réseau FTTH</div>
        <div class="header-sub">Redevance d'Occupation du Domaine Public · Département du Gers · Classification par cadastres</div>
    </div>
    <div class="header-badge">Gers Numérique</div>
</div>""", unsafe_allow_html=True)

st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-card total"><div class="kpi-label">Tronçons total</div>
    <div class="kpi-value total">{n_total:,}</div><div class="kpi-sub">réseau FTTH qualifié</div></div>
  <div class="kpi-card pub"><div class="kpi-label">Domaine public</div>
    <div class="kpi-value pub">{n_pub:,}</div><div class="kpi-sub">tronçons soumis RODP</div></div>
  <div class="kpi-card priv"><div class="kpi-label">Domaine privé</div>
    <div class="kpi-value priv">{n_priv:,}</div><div class="kpi-sub">tronçons hors RODP</div></div>
  <div class="kpi-card km"><div class="kpi-label">Longueur publique totale</div>
    <div class="kpi-value km">{km_pub:,.0f} m</div><div class="kpi-sub">linéaire soumis à redevance</div></div>
</div>""", unsafe_allow_html=True)

# ── KPIs longueur par commune ─────────────────────────────────────────────
# Removed individual commune KPI cards (Beaumarche, Samatan lengths) per user request
# if fd_pub is not None and len(fd_pub) > 0 and "commune" in fd_pub.columns:
#     _communes_actives = sorted(fd_pub["commune"].dropna().unique().tolist())
#     if len(_communes_actives) > 1:
#         _len_par_commune = fd_pub.groupby("commune")["longueur"].apply(
#             lambda x: pd.to_numeric(x, errors="coerce").sum()
#         )
#         _cards = ""
#         for _com in _communes_actives:
#             _km = _len_par_comune = _len_par_commune.get(_com, 0)
#             _cards += f'''<div class="kpi-card km"><div class="kpi-label">Long. publique · {_com}</div>
#               <div class="kpi-value km" style="font-size:20px;">{_km:,.0f} m</div>
#               <div class="kpi-sub">{_km/1000:.2f} km</div></div>'''
#         _ncols = len(_communes_actives)
#         st.markdown(
#             f'<div style="display:grid;grid-template-columns:repeat({_ncols},1fr);gap:14px;margin-bottom:16px;">'
#             + _cards + '</div>',
#             unsafe_allow_html=True
#         )

# ─────────────────────────────────────────────
# CARTE INTERACTIVE
# ─────────────────────────────────────────────
st.markdown('<div class="section-title">Carte interactive</div>', unsafe_allow_html=True)

# Centre automatique
center = [43.7537, 0.9258]
for gj in [fj_pub, fj_priv]:
    if gj and gj["features"]:
        try:
            coords = []
            for f in gj["features"][:300]:
                g = f["geometry"]
                t = g["type"]
                if t == "LineString":
                    coords.extend(g["coordinates"])
                elif t == "MultiLineString":
                    for part in g["coordinates"]:
                        coords.extend(part)
            if coords:
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]
                center = [(min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2]
                break
        except Exception:
            pass

m = folium.Map(location=center, zoom_start=13, tiles=None, control_scale=True)

folium.TileLayer(
    tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    attr="© OpenStreetMap © CARTO",
    name="CartoDB Dark",
    max_zoom=19, max_native_zoom=19,
).add_to(m)
folium.TileLayer(
    tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attr="© OpenStreetMap contributors",
    name="OpenStreetMap",
    max_zoom=22, max_native_zoom=19,
    show=False,
).add_to(m)

TT_FIELDS  = ["cm_support", "domaine", "longueur", "commune", "type_class", "zanro"]
TT_ALIASES = {
    "cm_support": "Support :",
    "domaine":    "Domaine :",
    "longueur":   "Longueur (m) :",
    "commune":    "Commune :",
    "type_class": "Classification :",
    "zanro":      "NRO :",
}
TT_STYLE = "background:#111827;color:#e8f4ff;font-size:12px;border:1px solid #1e3a5f;border-radius:6px;padding:8px;"


def add_network_layer(gj, name, default_color):
    if not gj or not gj["features"]:
        return
    sample = gj["features"][0]["properties"]
    fields  = [f for f in TT_FIELDS if f in sample]
    aliases = [TT_ALIASES.get(f, f + " :") for f in fields]
    GeoJson(
        gj, name=name,
        style_function=lambda f, dc=default_color: {
            "color":   get_color(f["properties"].get("cm_support"), dc),
            "weight":  2.5, "opacity": 0.9,
        },
        tooltip=GeoJsonTooltip(fields=fields, aliases=aliases,
                               localize=True, sticky=False, labels=True,
                               style=TT_STYLE) if fields else None,
    ).add_to(m)


def add_cadastre_layer(gj):
    if not gj or not gj["features"]:
        return
    sample = gj["features"][0]["properties"]
    cad_fields  = [f for f in ["commune", "section", "numero", "contenance"] if f in sample]
    cad_aliases = {"commune": "Commune :", "section": "Section :",
                   "numero": "Numéro :", "contenance": "Contenance (m²) :"}
    GeoJson(
        gj, name="Couche cadastrale",
        style_function=lambda f: {
            "fillColor":   "#ffe066",
            "color":       "#ccaa00",
            "weight":      0.8,
            "fillOpacity": 0.08,
            "opacity":     0.5,
        },
        tooltip=GeoJsonTooltip(
            fields=cad_fields,
            aliases=[cad_aliases.get(f, f + " :") for f in cad_fields],
            localize=True, sticky=False, labels=True, style=TT_STYLE
        ) if cad_fields else None,
    ).add_to(m)


# Cadastre en premier (fond) puis les réseaux par-dessus
add_cadastre_layer(fj_cad)
add_network_layer(fj_pub,  "Voiries publiques", "#00aaff")
add_network_layer(fj_priv, "Voiries privées",   "#ff8800")
folium.LayerControl(collapsed=False).add_to(m)

st_folium(m, height=640, use_container_width=True, returned_objects=[])

# ─────────────────────────────────────────────
# ONGLETS
# ─────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "  Détail tronçons",
    "  Répartition par support",
    "  Simulateur RODP",
])

# ── Onglet 1 : Détail tronçons ───────────────────────────────────────────
with tab1:
    combined = pd.concat([fd_pub, fd_priv], ignore_index=True)
    if len(combined) > 0:
        cols_show = [c for c in ["domaine", "cm_support", "longueur", "commune", "type_class", "zanro", "cm_code"]
                     if c in combined.columns]
        if cols_show:
            disp = combined[cols_show].copy()
            if "longueur" in disp.columns:
                disp["longueur"] = pd.to_numeric(disp["longueur"], errors="coerce").round(1)
            rename = {
                "domaine":    "Domaine",
                "cm_support": "Support",
                "longueur":   "Long. (m)",
                "commune":    "Commune",
                "type_class": "Classification",
                "zanro":      "NRO",
                "cm_code":    "Code tronçon",
            }
            disp.rename(columns=rename, inplace=True)
            st.dataframe(disp, use_container_width=True, height=380, hide_index=True)
        else:
            st.info("Pas d'attributs à afficher")
    else:
        st.info("Aucun tronçon sélectionné")

# ── Onglet 2 : Répartition par support ──────────────────────────────────
with tab2:
    stat_src = pd.concat([
        fast_filter_df(dfs.get("pub_voiries"),  True, sel_dom, sel_sup, sel_commune),
        fast_filter_df(dfs.get("priv_voiries"), True, sel_dom, sel_sup, sel_commune),
    ], ignore_index=True)

    if len(stat_src) > 0 and "cm_support" in stat_src.columns:
        if "domaine" in stat_src.columns:
            stat = stat_src.groupby(["cm_support", "domaine"]).size().reset_index(name="nb")
            fig = px.bar(stat, x="cm_support", y="nb", color="domaine",
                         color_discrete_map={"Public": "#00aaff", "Privé": "#ff8800"},
                         barmode="stack",
                         labels={"cm_support": "Type de support", "nb": "Nb tronçons", "domaine": "Domaine"})
        else:
            stat = stat_src.groupby("cm_support").size().reset_index(name="nb")
            fig = px.bar(stat, x="cm_support", y="nb",
                         labels={"cm_support": "Type de support", "nb": "Nb tronçons"})
        fig.update_layout(
            paper_bgcolor="#0a0e1a", plot_bgcolor="#0d1220", font_color="#9bb5cf",
            font_family="DM Sans",
            xaxis=dict(gridcolor="#1a2a3e", tickangle=-35),
            yaxis=dict(gridcolor="#1a2a3e"),
            legend=dict(bgcolor="#0d1220", bordercolor="#1e3a5f"),
            margin=dict(l=0, r=0, t=10, b=70), height=340,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Pas de données à afficher")

# ── Onglet 3 : Simulateur RODP ───────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-title">Simulateur de Redevance d\'Occupation du Domaine Public</div>',
                unsafe_allow_html=True)

    # ── Rappel réglementaire ─────────────────────────────────────────────
    col_tarif, col_info = st.columns([1, 2])
    with col_tarif:
        tarif_rodp = st.number_input(
            "Tarif RODP (€/m/an)",
            min_value=0.0, max_value=10.0, value=0.040, step=0.001, format="%.4f",
            help="Tarif fixé par délibération communale · Art. R.20-52 CPCE · base légale : 40 €/km/an"
        )
    with col_info:
        st.markdown("""
        <div style="background:#0d1a2e;border:1px solid #1e3a5f;border-radius:8px;
                    padding:12px 16px;margin-top:4px;font-size:12px;color:#9bb5cf;">
            <b style="color:#5bc4ff;"> Rappel réglementaire</b><br>
            La RODP est calculée sur la longueur de réseau en <b>domaine public</b> uniquement.
            Le tarif est fixé par délibération communale, dans le strict respect des plafonds légaux
            prévus à l'<b>article R. 20-52 du Code des postes et des communications électroniques</b>,
            actualisés au 1<sup>er</sup> janvier de chaque année selon l'index des travaux publics (TP01).
        </div>""", unsafe_allow_html=True)

    df_pub_r = dfs.get("pub_voiries", pd.DataFrame())

    if len(df_pub_r) > 0 and "commune" in df_pub_r.columns:
        _lr = df_pub_r[["commune"]].copy().reset_index(drop=True)
        _lr["_len"] = pd.to_numeric(df_pub_r["longueur"], errors="coerce").fillna(0).values

        by_c = _lr.groupby("commune")["_len"].sum().reset_index()
        by_c.columns = ["Commune", "Longueur pub (m)"]
        by_c["Longueur pub (km)"]   = (by_c["Longueur pub (m)"] / 1000).round(3)
        by_c["Montant annuel (€)"]  = (by_c["Longueur pub (m)"] * tarif_rodp).round(2)
        by_c["Longueur pub (m)"]    = by_c["Longueur pub (m)"].round(1)

        tot = pd.DataFrame([{
            "Commune":            " TOTAL",
            "Longueur pub (m)":   round(float(by_c["Longueur pub (m)"].sum()), 1),
            "Longueur pub (km)":  round(float(by_c["Longueur pub (km)"].sum()), 3),
            "Montant annuel (€)": round(float(by_c["Montant annuel (€)"].sum()), 2),
        }])
        by_c_disp = pd.concat([by_c, tot], ignore_index=True)
        st.dataframe(
            by_c_disp.style.format({
                "Longueur pub (m)":   "{:,.1f}",
                "Longueur pub (km)":  "{:,.3f}",
                "Montant annuel (€)": "{:,.2f} €",
            }),
            use_container_width=True, hide_index=True, height=200
        )
        total_m   = float(by_c["Longueur pub (m)"].sum())
        total_eur = float(by_c["Montant annuel (€)"].sum())
        c1, c2, c3 = st.columns(3)
        c1.metric("Longueur publique totale", f"{total_m:,.0f} m")
        c2.metric("Montant RODP annuel total", f"{total_eur:,.0f} €")
        c3.metric("Tarif appliqué", f"{tarif_rodp:.4f} €/m/an")

        if len(by_c) > 0:
            fig_rodp = px.bar(
                by_c, x="Commune", y="Montant annuel (€)",
                color="Commune", text="Montant annuel (€)",
                labels={"Montant annuel (€)": "Montant (€)"},
                title="Montant RODP annuel par commune"
            )
            fig_rodp.update_traces(texttemplate="%{text:,.0f} €", textposition="outside")
            fig_rodp.update_layout(
                paper_bgcolor="#0a0e1a", plot_bgcolor="#0d1220", font_color="#9bb5cf",
                font_family="DM Sans", showlegend=False, title_font_color="#e8edf5",
                xaxis=dict(gridcolor="#1a2a3e"),
                yaxis=dict(gridcolor="#1a2a3e"),
                margin=dict(l=0, r=0, t=40, b=20), height=300,
            )
            st.plotly_chart(fig_rodp, use_container_width=True)
    elif len(df_pub_r) > 0:
        st.warning(" La colonne 'commune' est absente des données publiques.")
    else:
        st.info("Aucun tronçon public chargé.")

