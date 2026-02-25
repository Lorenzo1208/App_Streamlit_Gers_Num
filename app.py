import streamlit as st
import geopandas as gpd
import folium
from folium import GeoJson, GeoJsonTooltip
from streamlit_folium import st_folium
import pandas as pd
import os
import plotly.express as px

# 
# CONFIG
# 
st.set_page_config(
    page_title="SIG RODP – Gers Numérique",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 
# CSS
# 
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
[data-testid="stHeader"]    { display:none !important; height:0 !important; }
[data-testid="stDecoration"]{ display:none !important; }
section[data-testid="stSidebar"] > div:first-child { padding-top: 1rem !important; }
::-webkit-scrollbar { width:5px; } ::-webkit-scrollbar-track { background:#0a0e1a; }
::-webkit-scrollbar-thumb { background:#1e3a5f; border-radius:3px; }
</style>
""", unsafe_allow_html=True)

# 
# COULEURS
# 
SUPPORT_COLORS = {
    "Souterrain RIP construit":    "#00aaff",
    "Souterrain RIP RAF":          "#0066cc",
    "Chambre":                     "#66ccff",
    "Aérien Enedis":               "#ffaa00",
    "Aérien Orange":               "#ff7700",
    "Aérien RIP":                  "#ffdd00",
    "Aéro-souterrain":             "#ff44aa",
    "Aéro-souterrain Orange":      "#cc44aa",
    "Façade":                      "#44ff88",
    "Réseau en parcelle agricole": "#ff4444",
    "Souterrain Orange":           "#9966ff",
    "Souterrain Tiers":            "#cc99ff",
    "sans_tag":                    "#888888",
}
_color_lookup = {k.lower(): v for k, v in SUPPORT_COLORS.items()}

def get_color(val, fallback="#aaaaaa"):
    return _color_lookup.get(str(val).strip().lower(), fallback) if val else fallback

# 
# CHARGEMENT + PRÉ-CALCUL GEOJSON (mis en cache - exécuté UNE seule fois)
# 
DATA_DIR = os.environ.get("SIG_DATA_DIR", "data")

def _prepare(gdf):
    """Nettoie les types, simplifie les géométries, réduit aux colonnes utiles."""
    g = gdf.copy()
    # Normaliser la colonne de longueur (plusieurs noms possibles dans les DBF)
    LENGTH_CANDIDATES = ["longueur","LONGUEUR","Shape_Leng","shape_leng",
                         "Shape_Length","shape_length","longueur_m","LONGUEUR_M","len","LEN"]
    if "longueur" not in g.columns:
        for cand in LENGTH_CANDIDATES:
            if cand in g.columns:
                g = g.rename(columns={cand: "longueur"})
                break
    # Normaliser les colonnes clés (case-insensitive)
    col_map = {}
    for col in g.columns:
        cl = col.lower()
        if cl in ("domaine","cm_support","commune") and col != cl:
            col_map[col] = cl
    if col_map:
        g = g.rename(columns=col_map)
    # Garder géométrie + colonnes utiles
    useful = ["geometry","domaine","cm_support","longueur","commune",
              "id","nature","statut","gestionnaire"]
    g = g[[c for c in useful if c in g.columns]].copy()
    for col in g.columns:
        if col == "geometry":
            continue
        try:
            if pd.api.types.is_datetime64_any_dtype(g[col]):
                g[col] = g[col].astype(str)
            elif g[col].dtype == object:
                g[col] = g[col].apply(
                    lambda x: str(x) if not isinstance(x, (str,int,float,bool,type(None))) else x)
            else:
                g[col] = g[col].where(pd.notna(g[col]), None)
        except Exception:
            g[col] = g[col].astype(str)
    # Simplification légère → moins de points à envoyer au navigateur
    g["geometry"] = g["geometry"].simplify(0.00005, preserve_topology=True)
    return g

@st.cache_data(show_spinner="Chargement et préparation des données…")
def load_all():
    """
    Chargement dynamique : scanne tout le dossier data/.
    Convention de nommage attendue :
      prive_{commune}.shp  → réseau privé
      public_{commune}.shp → réseau public
      Emprise.shp          → emprise LiDAR
      (autres fichiers ignorés)
    """
    import re, glob

    LENGTH_CANDS = ["longueur","LONGUEUR","Shape_Leng","shape_leng",
                    "Shape_Length","shape_length","longueur_m","LONGUEUR_M","len","LEN"]

    def _norm_df(df):
        """Normalise noms de colonnes + types."""
        if "longueur" not in df.columns:
            for c in LENGTH_CANDS:
                if c in df.columns:
                    df = df.rename(columns={c: "longueur"})
                    break
        col_map = {c: c.lower() for c in df.columns
                   if c.lower() in ("domaine","cm_support","commune") and c != c.lower()}
        if col_map:
            df = df.rename(columns=col_map)
        for col in df.columns:
            try:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    df[col] = df[col].astype(str)
            except Exception:
                pass
        return df

    # Déduplication des chemins (Windows : glob insensible à la casse → chaque fichier
    # apparaît 2x si on combine *.shp + *.SHP, ce qui doublerait tous les tronçons)
    _seen_lower = set()
    shp_files = []
    for _p in (glob.glob(os.path.join(DATA_DIR, "*.shp")) +
               glob.glob(os.path.join(DATA_DIR, "*.SHP"))):
        _pk = os.path.normcase(_p)
        if _pk not in _seen_lower:
            _seen_lower.add(_pk)
            shp_files.append(_p)

    #  Fichiers exclus (doublons confirmés par analyse spatiale) 
    # Chaque paire a été comparée géométriquement (buffer 5 m, échantillon 300):
    #   public_beaumarche      → doublon de public_beaumarche_second_diff (overlap 613%)
    #   prive_beaumarche_25    → doublon de prive_beaumarche              (overlap 238%)
    #   parcours_priv_voiries  → doublon de prive_samatan                 (overlap 194%)
    #   sam_privé              → doublon de prive_samatan                 (overlap 180%)
    EXCLUDED_FNAMES = {
        "public_beaumarche.shp",          # remplacé par public_beaumarche_second_diff
        "prive_beaumarche_25.shp",        # remplacé par prive_beaumarche
        "parcours_priv_voiries.shp",      # remplacé par prive_samatan
        "sam_priv\u00e9.shp",             # remplacé par prive_samatan (sam_privé)
    }

    pub_frames  = []
    priv_frames = []
    emprise_gdf = None

    for path in shp_files:
        fname = os.path.basename(path)
        name  = fname.replace(".shp","").replace(".SHP","").lower()

        #  Exclure les fichiers redondants 
        if fname in EXCLUDED_FNAMES:
            continue

        #  Emprise / LiDAR 
        if name in ("emprise", "lidar", "samatan_lidar"):
            try:
                g = gpd.read_file(path)
                if g.crs and g.crs.to_epsg() != 4326:
                    g = g.to_crs(epsg=4326)
                emprise_gdf = g
            except Exception as e:
                st.warning(f"Impossible de charger {fname}: {e}")
            continue

        #  Réseau fibre (prive_ / public_) 
        if name.startswith("prive_") or name.startswith("public_"):
            domaine_val = "Privé"  if name.startswith("prive_")  else "Public"
            # Extraire la commune depuis le nom
            commune_raw = re.sub(r"^(prive|public)_", "", name)
            commune_raw = re.sub(r"_25cm$|_25$|_second_diff$|_second$", "", commune_raw)
            commune_val = commune_raw.replace("_"," ").title()

            try:
                g = gpd.read_file(path)
                if g.crs and g.crs.to_epsg() != 4326:
                    g = g.to_crs(epsg=4326)
                # Injecter domaine et commune si absents
                if "domaine" not in g.columns:
                    g["domaine"] = domaine_val
                if "commune" not in g.columns:
                    g["commune"] = commune_val
                if domaine_val == "Public":
                    pub_frames.append(g)
                else:
                    priv_frames.append(g)
            except Exception as e:
                st.warning(f"Impossible de charger {fname}: {e}")
            continue

        #  Anciens noms (compatibilité) 
        if name in ("parcours_pub_voiries",):
            try:
                g = gpd.read_file(path)
                if g.crs and g.crs.to_epsg() != 4326:
                    g = g.to_crs(epsg=4326)
                if "domaine" not in g.columns: g["domaine"] = "Public"
                # Commune : renseigner "Samatan" si colonne absente ou entierement vide
                if "commune" not in g.columns or g["commune"].isna().all():
                    g["commune"] = "Samatan"
                pub_frames.append(g)
            except Exception: pass
            continue
        if name in ("parcours_priv_voiries", "sam_privé", "sam_prive"):
            try:
                g = gpd.read_file(path)
                if g.crs and g.crs.to_epsg() != 4326:
                    g = g.to_crs(epsg=4326)
                if "domaine" not in g.columns: g["domaine"] = "Privé"
                priv_frames.append(g)
            except Exception: pass
            continue
        # Autres fichiers ignorés (cadastre, découpe, etc.)

    #  Fusionner public + privé 
    pub_gdf_merged  = gpd.GeoDataFrame(pd.concat(pub_frames,  ignore_index=True),
                                       crs="EPSG:4326") if pub_frames  else None
    priv_gdf_merged = gpd.GeoDataFrame(pd.concat(priv_frames, ignore_index=True),
                                       crs="EPSG:4326") if priv_frames else None

    gdfs = {
        "pub_voiries":  pub_gdf_merged,
        "priv_voiries": priv_gdf_merged,
        "lidar":        emprise_gdf,
    }
    gjs, dfs = {}, {}
    for key, gdf in gdfs.items():
        if gdf is not None:
            gjs[key]  = _prepare(gdf).__geo_interface__
            df = gdf.drop(columns="geometry", errors="ignore").copy()
            dfs[key]  = _norm_df(df)
        else:
            gjs[key]  = None
            dfs[key]  = pd.DataFrame()
    return gdfs, gjs, dfs
def _demo():
    import numpy as np
    from shapely.geometry import LineString
    rng = np.random.default_rng(42)
    blon, blat = 0.9258, 43.7537
    def rl(n=5):
        return LineString(zip(blon + rng.uniform(-0.05,0.05,n).cumsum()*0.01,
                              blat + rng.uniform(-0.05,0.05,n).cumsum()*0.01))
    sp = ["Souterrain RIP construit","Souterrain RIP RAF","Aérien Enedis","Aérien Orange"]
    sv = ["Façade","Réseau en parcelle agricole","Souterrain Orange","Aéro-souterrain"]
    villes = ["Samatan","Lombez","Beaumarché"]
    pub  = gpd.GeoDataFrame([{"geometry":rl(),"domaine":"Public",
        "cm_support":rng.choice(sp),"longueur":round(rng.uniform(50,500),2),
        "commune":rng.choice(villes)} for _ in range(350)], crs="EPSG:4326")
    priv = gpd.GeoDataFrame([{"geometry":rl(),"domaine":"Privé",
        "cm_support":rng.choice(sv),"longueur":round(rng.uniform(30,300),2),
        "commune":rng.choice(villes)} for _ in range(200)], crs="EPSG:4326")
    gdfs = {"pub_voiries":pub,"priv_voiries":priv,"sam_prive":None,"lidar":None}
    gjs, dfs = {}, {}
    for k,g in gdfs.items():
        if g is not None:
            gjs[k] = _prepare(g).__geo_interface__
            dfs[k] = g.drop(columns="geometry")
        else:
            gjs[k], dfs[k] = None, pd.DataFrame()
    return gdfs, gjs, dfs

gdfs, gjs, dfs = load_all()
demo_mode = all(v is None for v in gdfs.values())
if demo_mode:
    gdfs, gjs, dfs = _demo()

all_df = pd.concat([dfs.get("pub_voiries", pd.DataFrame()),
                    dfs.get("priv_voiries", pd.DataFrame())], ignore_index=True)

# 
# FILTRAGE RAPIDE (dicts Python, pas de GeoDataFrame)
# 
def fast_filter_gj(gj, show, sel_dom, sel_sup, commune):
    """Filtre un GeoJSON dict - ultra-rapide car pas de copie GDF."""
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
        if commune != "Toutes" and "commune" in p and p["commune"] != commune:
            continue
        feats.append(f)
    return {"type":"FeatureCollection","features":feats} if feats else None

def fast_filter_df(df, show, sel_dom, sel_sup, commune):
    if not show or df is None or len(df)==0:
        return pd.DataFrame()
    d = df
    if "domaine" in d.columns    and sel_dom: d = d[d["domaine"].isin(sel_dom)]
    if "cm_support" in d.columns and sel_sup: d = d[d["cm_support"].isin(sel_sup)]
    if commune != "Toutes" and "commune" in d.columns: d = d[d["commune"]==commune]
    return d.reset_index(drop=True)

# 
# SIDEBAR
# 
with st.sidebar:
    st.markdown("""
    <div style='text-align:center;margin-bottom:20px;'>
        <div style='font-size:22px;'></div>
        <div style='font-size:14px;font-weight:900;color:#5bc4ff;'>SIG RODP</div>
        <div style='font-size:9px;color:#3d6e9e;letter-spacing:.1em;text-transform:uppercase;'>Gers Numérique</div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-title">Couches</div>', unsafe_allow_html=True)
    show_pub   = st.checkbox("Voiries publiques", value=True)
    show_priv  = st.checkbox("Voiries privées",   value=True)
    show_lidar = st.checkbox("Emprise LiDAR",     value=True)

    st.markdown('<div class="section-title">Domaine</div>', unsafe_allow_html=True)
    sel_dom = st.multiselect("Domaine", ["Public","Privé"], default=["Public","Privé"])

    st.markdown('<div class="section-title">Type de support</div>', unsafe_allow_html=True)
    all_sup = sorted(all_df["cm_support"].dropna().unique().tolist()) if "cm_support" in all_df.columns else list(SUPPORT_COLORS)
    sel_sup = st.multiselect("Support réseau", all_sup, default=all_sup, placeholder="Tous…")
    if not sel_sup: sel_sup = all_sup

    st.markdown('<div class="section-title">Commune</div>', unsafe_allow_html=True)
    communes = ["Toutes"] + (sorted(all_df["commune"].dropna().unique().tolist()) if "commune" in all_df.columns else [])
    sel_commune = st.selectbox("Commune", communes)

    st.markdown('<div class="section-title">Légende</div>', unsafe_allow_html=True)
    for name, color in SUPPORT_COLORS.items():
        st.markdown(f'<div class="legend-item"><div class="legend-dot" style="background:{color};"></div>'
                    f'<span style="color:#9bb5cf;">{name}</span></div>', unsafe_allow_html=True)

    #  Infos de chargement 
    st.markdown('<div class="section-title">Données chargées</div>', unsafe_allow_html=True)

    def _info(key, label, color):
        gdf = gdfs.get(key)
        df  = dfs.get(key, pd.DataFrame())
        if gdf is not None and len(gdf) > 0:
            n = len(gdf)
            communes_found = sorted(df["commune"].dropna().unique().tolist()) if "commune" in df.columns else []
            comm_str = ", ".join(communes_found) if communes_found else "-"
            st.markdown(
                f'''<div style="background:#0d1a2e;border:1px solid {color}33;border-left:3px solid {color};
                border-radius:6px;padding:8px 10px;margin-bottom:6px;font-size:11px;">
                <span style="color:{color};font-weight:700;">{label}</span>
                <span style="color:#5a7fa8;"> · {n:,} tronçons</span><br>
                <span style="color:#3d6e9e;">{comm_str}</span>
                </div>''', unsafe_allow_html=True)
        else:
            st.markdown(
                f'''<div style="background:#1a0d0d;border:1px solid #3a1e1e;border-left:3px solid #553333;
                border-radius:6px;padding:8px 10px;margin-bottom:6px;font-size:11px;">
                <span style="color:#664444;font-weight:700;">{label}</span>
                <span style="color:#443333;"> · non chargé</span>
                </div>''', unsafe_allow_html=True)

    _info("pub_voiries",  " Public",  "#00aaff")
    _info("priv_voiries", " Privé",   "#ff8800")
    gdf_lid = gdfs.get("lidar")
    if gdf_lid is not None:
        st.markdown(f'''<div style="background:#0d1a2e;border:1px solid #44ff8833;border-left:3px solid #44ff88;
            border-radius:6px;padding:8px 10px;margin-bottom:6px;font-size:11px;">
            <span style="color:#44ff88;font-weight:700;"> LiDAR/Emprise</span>
            <span style="color:#5a7fa8;"> · {len(gdf_lid):,} entités</span>
            </div>''', unsafe_allow_html=True)
    else:
        st.markdown('''<div style="background:#1a0d0d;border:1px solid #3a1e1e;border-left:3px solid #553333;
            border-radius:6px;padding:8px 10px;margin-bottom:6px;font-size:11px;">
            <span style="color:#664444;font-weight:700;"> LiDAR/Emprise</span>
            <span style="color:#443333;"> · non chargé</span>
            </div>''', unsafe_allow_html=True)

    if demo_mode:
        st.markdown('<div style="margin-top:16px;background:#1a1a0d;border:1px solid #333300;'
                    'border-radius:8px;padding:10px;font-size:11px;color:#aaa830;">'
                    ' Mode démo</div>', unsafe_allow_html=True)

    #  Export 
    st.markdown('<div class="section-title">Télécharger</div>', unsafe_allow_html=True)
    _df_pub_exp  = dfs.get("pub_voiries",  pd.DataFrame())
    _df_priv_exp = dfs.get("priv_voiries", pd.DataFrame())
    _full_export = pd.concat([_df_pub_exp, _df_priv_exp], ignore_index=True)
    if len(_full_export) > 0:
        _csv = _full_export.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(" CSV - tous tronçons", _csv, "rodp_troncons.csv",
                           "text/csv", use_container_width=True)
        try:
            import io as _io
            _buf = _io.BytesIO()
            with pd.ExcelWriter(_buf, engine="openpyxl") as _w:
                _full_export.to_excel(_w, sheet_name="Tous tronçons", index=False)
                if "commune" in _df_pub_exp.columns and "longueur" in _df_pub_exp.columns and len(_df_pub_exp) > 0:
                    _sc = _df_pub_exp.groupby("commune")["longueur"].apply(
                        lambda x: pd.to_numeric(x, errors="coerce").sum()
                    ).reset_index()
                    _sc.columns = ["Commune", "Longueur_pub_m"]
                    _sc.to_excel(_w, sheet_name="Synthèse RODP", index=False)
            st.download_button(" Excel (avec synthèse)", _buf.getvalue(),
                               "rodp_troncons.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)
        except Exception as _xe:
            st.caption(f"Excel : {_xe}")
    else:
        st.caption("Aucune donnée chargée")

# 
# APPLIQUER LES FILTRES
# 
fj_pub  = fast_filter_gj(gjs.get("pub_voiries"),  show_pub,   sel_dom, sel_sup, sel_commune)
fj_priv = fast_filter_gj(gjs.get("priv_voiries"), show_priv,  sel_dom, sel_sup, sel_commune)
fj_lid  = fast_filter_gj(gjs.get("lidar"),        show_lidar, [],      [],      "Toutes")

fd_pub  = fast_filter_df(dfs.get("pub_voiries"),  show_pub,  sel_dom, sel_sup, sel_commune)
fd_priv = fast_filter_df(dfs.get("priv_voiries"), show_priv, sel_dom, sel_sup, sel_commune)

# 
# MÉTRIQUES
# 
n_pub   = len(fj_pub["features"])  if fj_pub  else 0
n_priv  = len(fj_priv["features"]) if fj_priv else 0
n_total = n_pub + n_priv
def _sum_length(df, gdf_orig):
    """Somme la longueur depuis colonne ou géométrie en fallback."""
    if df is not None and len(df) > 0:
        if "longueur" in df.columns:
            val = pd.to_numeric(df["longueur"], errors="coerce").sum()
            if val > 0:
                return val
    # Fallback : calculer depuis les géométries (reprojeté Lambert-93)
    if gdf_orig is not None and len(gdf_orig) > 0:
        try:
            return gdf_orig.to_crs(epsg=2154).geometry.length.sum()
        except Exception:
            pass
    return 0.0

km_pub  = _sum_length(fd_pub,  gdfs.get("pub_voiries"))
km_priv = _sum_length(fd_priv, gdfs.get("priv_voiries"))

# 
# HEADER + KPIs
# 
st.markdown("""
<div class="header-banner">
    <div>
        <div class="header-title">Classification RODP – Réseau FTTH</div>
        <div class="header-sub">Redevance d'Occupation du Domaine Public · Département du Gers</div>
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
  <div class="kpi-card km"><div class="kpi-label">Longueur publique</div>
    <div class="kpi-value km">{km_pub:,.0f} m</div><div class="kpi-sub">linéaire soumis à redevance</div></div>
</div>""", unsafe_allow_html=True)

# 
# ALERTES QUALITÉ DES DONNÉES
# 
_aq_full = pd.concat([dfs.get("pub_voiries", pd.DataFrame()),
                      dfs.get("priv_voiries", pd.DataFrame())], ignore_index=True)
if len(_aq_full) > 0:
    _aq_alerts = []
    if "domaine" in _aq_full.columns:
        _m = int(_aq_full["domaine"].isna().sum())
        if _m: _aq_alerts.append(f"{_m} tronçons sans domaine")
    if "cm_support" in _aq_full.columns:
        _m = int(_aq_full["cm_support"].isna().sum())
        if _m: _aq_alerts.append(f"{_m} tronçons sans support")
    if "longueur" in _aq_full.columns:
        _m = int(pd.to_numeric(_aq_full["longueur"], errors="coerce").isna().sum())
        if _m: _aq_alerts.append(f"{_m} tronçons sans longueur")
    if _aq_alerts:
        st.warning(" Données incomplètes : " + " · ".join(_aq_alerts))

# 
# CARTE PLEINE LARGEUR
# 
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
                    for part in g["coordinates"]: coords.extend(part)
            if coords:
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]
                center = [(min(lats)+max(lats))/2, (min(lons)+max(lons))/2]
                break
        except Exception:
            pass

m = folium.Map(
    location=center, zoom_start=12,
    tiles=None,
    control_scale=True,
)
# Fond sombre CartoDB (zoom 19 max)
folium.TileLayer(
    tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    attr="© OpenStreetMap © CARTO",
    name="CartoDB Dark",
    max_zoom=19,
    max_native_zoom=19,
).add_to(m)
# Fond OSM standard (zoom 22) - pour zoomer très fort
folium.TileLayer(
    tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attr="© OpenStreetMap contributors",
    name="OpenStreetMap",
    max_zoom=22,
    max_native_zoom=19,
    show=False,
).add_to(m)

TT_FIELDS  = ["cm_support","domaine","longueur","commune"]
TT_ALIASES = {"cm_support":"Support:","domaine":"Domaine:","longueur":"Longueur (m):","commune":"Commune:"}
TT_STYLE   = "background:#111827;color:#e8f4ff;font-size:12px;border:1px solid #1e3a5f;border-radius:6px;padding:8px;"

def add_layer(gj, name, default_color, color_col="cm_support"):
    if not gj or not gj["features"]: return
    sample = gj["features"][0]["properties"]
    fields  = [f for f in TT_FIELDS if f in sample]
    aliases = [TT_ALIASES.get(f, f+":") for f in fields]
    GeoJson(
        gj, name=name,
        style_function=lambda f, cc=color_col, dc=default_color: {
            "color":   get_color(f["properties"].get(cc) if cc else None, dc),
            "weight":  2.5, "opacity": 0.9,
        },
        tooltip=GeoJsonTooltip(fields=fields, aliases=aliases,
                               localize=True, sticky=False, labels=True,
                               style=TT_STYLE) if fields else None,
    ).add_to(m)

add_layer(fj_pub,  "Voiries publiques", "#00aaff")
add_layer(fj_priv, "Voiries privées",   "#ff8800")
add_layer(fj_lid,  "Emprise LiDAR",     "#44ff88", color_col=None)
folium.LayerControl(collapsed=False).add_to(m)

# Carte pleine largeur, height max
st_folium(m, height=640, use_container_width=True, returned_objects=[])

# 
# ONGLETS SOUS LA CARTE
# 
tab1, tab2, tab3, tab4 = st.tabs([
    "  Détail tronçons",
    "  Répartition par support",
    "  Simulateur RODP",
    "  Qualité données",
])

with tab1:
    combined = pd.concat([fd_pub, fd_priv], ignore_index=True)
    if len(combined) > 0:
        cols = [c for c in ["domaine","cm_support","longueur","commune"] if c in combined.columns]
        if cols:
            disp = combined[cols].copy()
            if "longueur" in disp.columns: disp["longueur"] = disp["longueur"].round(1)
            rename = {"domaine":"Domaine","cm_support":"Support","longueur":"Long.(m)","commune":"Commune"}
            disp.rename(columns=rename, inplace=True)
            st.dataframe(disp, use_container_width=True, height=350, hide_index=True)
        else:
            st.info("Pas d'attributs à afficher")
    else:
        st.info("Aucun tronçon sélectionné")

with tab2:
    stat_src = filter_df_full = pd.concat([
        fast_filter_df(dfs.get("pub_voiries"),  True, sel_dom, sel_sup, sel_commune),
        fast_filter_df(dfs.get("priv_voiries"), True, sel_dom, sel_sup, sel_commune),
    ], ignore_index=True)
    if len(stat_src) > 0 and "cm_support" in stat_src.columns:
        if "domaine" in stat_src.columns:
            stat = stat_src.groupby(["cm_support","domaine"]).size().reset_index(name="nb")
            fig = px.bar(stat, x="cm_support", y="nb", color="domaine",
                         color_discrete_map={"Public":"#00aaff","Privé":"#ff8800"},
                         barmode="stack",
                         labels={"cm_support":"Type de support","nb":"Nb tronçons","domaine":"Domaine"})
        else:
            stat = stat_src.groupby("cm_support").size().reset_index(name="nb")
            fig = px.bar(stat, x="cm_support", y="nb",
                         labels={"cm_support":"Type de support","nb":"Nb tronçons"})
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

# 
# ONGLET 3 : SIMULATEUR RODP
# 
with tab3:
    st.markdown('<div class="section-title">Simulateur de Redevance d\'Occupation du Domaine Public</div>',
                unsafe_allow_html=True)

    col_tarif, col_info = st.columns([1, 2])
    with col_tarif:
        tarif_rodp = st.number_input(
            "Tarif RODP (€/m/an)",
            min_value=0.0, max_value=10.0, value=0.04, step=0.001, format="%.4f",
            help="Tarif légal maximum indicatif : 0.04 €/m/an (40 €/km/an)"
        )
    with col_info:
        st.markdown("""
        <div style="background:#0d1a2e;border:1px solid #1e3a5f;border-radius:8px;
                    padding:12px 16px;margin-top:4px;font-size:12px;color:#9bb5cf;">
            <b style="color:#5bc4ff;"> Rappel réglementaire</b><br>
            La RODP est calculée sur la longueur de réseau en <b>domaine public</b> uniquement.
            Le tarif est fixé par délibération communale (max légal ~40 €/km/an).
        </div>""", unsafe_allow_html=True)

    df_pub_r  = dfs.get("pub_voiries", pd.DataFrame())
    gdf_pub_r = gdfs.get("pub_voiries")

    if len(df_pub_r) > 0 and "commune" in df_pub_r.columns:
        # Longueur : colonne si disponible et non nulle, sinon calcul géométrique Lambert-93
        _lr = df_pub_r[["commune"]].copy().reset_index(drop=True)
        if "longueur" in df_pub_r.columns and pd.to_numeric(df_pub_r["longueur"], errors="coerce").sum() > 0:
            _lr["_len"] = pd.to_numeric(df_pub_r["longueur"], errors="coerce").values
        elif gdf_pub_r is not None:
            st.caption(" Longueur calculée depuis la géométrie (colonne absente dans les données)")
            _lr["_len"] = gdf_pub_r.to_crs(epsg=2154).geometry.length.reset_index(drop=True).values
        else:
            _lr["_len"] = 0.0

        by_c = _lr.groupby("commune")["_len"].sum().reset_index()
        by_c.columns = ["Commune", "Longueur pub (m)"]
        by_c["Longueur pub (km)"] = (by_c["Longueur pub (m)"] / 1000).round(3)
        by_c["Montant annuel (€)"] = (by_c["Longueur pub (m)"] * tarif_rodp).round(2)
        by_c["Longueur pub (m)"]   = by_c["Longueur pub (m)"].round(1)
        tot = pd.DataFrame([{"Commune": " TOTAL",
                              "Longueur pub (m)":  round(float(by_c["Longueur pub (m)"].sum()), 1),
                              "Longueur pub (km)": round(float(by_c["Longueur pub (km)"].sum()), 3),
                              "Montant annuel (€)": round(float(by_c["Montant annuel (€)"].sum()), 2)}])
        by_c_disp = pd.concat([by_c, tot], ignore_index=True)
        st.dataframe(
            by_c_disp.style.format({"Longueur pub (m)": "{:,.1f}",
                                     "Longueur pub (km)": "{:,.3f}",
                                     "Montant annuel (€)": "{:,.2f} €"}),
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
        st.warning(" La colonne 'commune' est absente des données publiques. Vérifiez les shapefiles.")
    else:
        st.info("Aucun tronçon public chargé.")

# 
# ONGLET 4 : QUALITÉ DES DONNÉES
# 
with tab4:
    st.markdown('<div class="section-title">Audit qualité du réseau FTTH</div>', unsafe_allow_html=True)

    _q_full = pd.concat([dfs.get("pub_voiries", pd.DataFrame()),
                         dfs.get("priv_voiries", pd.DataFrame())], ignore_index=True)
    if len(_q_full) > 0:
        n_total_q = len(_q_full)

        #  Indicateurs de complétude 
        cols_check = {
            "domaine":    "Domaine (Public/Privé)",
            "cm_support": "Type de support",
            "longueur":   "Longueur (m)",
            "commune":    "Commune",
        }
        q_rows = []
        for col, label in cols_check.items():
            if col in _q_full.columns:
                if col == "longueur":
                    n_ok = int(pd.to_numeric(_q_full[col], errors="coerce").notna().sum())
                else:
                    n_ok = int(_q_full[col].notna().sum())
                n_ko = n_total_q - n_ok
                pct  = round(100 * n_ok / n_total_q, 1)
                q_rows.append({"Champ": label, "Renseignés": n_ok, "Manquants": n_ko,
                               "Complétude %": pct})
        if q_rows:
            df_q = pd.DataFrame(q_rows)
            st.dataframe(
                df_q.style.format({"Complétude %": "{:.1f}%"})
                          .background_gradient(subset=["Complétude %"],
                                               cmap="RdYlGn", vmin=50, vmax=100),
                use_container_width=True, hide_index=True
            )

        #  Tableau croisé support × domaine 
        st.markdown('<div class="section-title">Répartition : Type de support × Domaine</div>',
                    unsafe_allow_html=True)
        if "cm_support" in _q_full.columns and "domaine" in _q_full.columns:
            _xt = _q_full.groupby(["cm_support", "domaine"]).agg(
                Tronçons=("cm_support", "count")
            ).reset_index()
            if "longueur" in _q_full.columns:
                _xt_l = _q_full.groupby(["cm_support", "domaine"])["longueur"].apply(
                    lambda x: pd.to_numeric(x, errors="coerce").sum()
                ).reset_index()
                _xt_l.columns = ["cm_support", "domaine", "Longueur (m)"]
                _xt = _xt.merge(_xt_l, on=["cm_support", "domaine"])
                _xt["Longueur (m)"] = _xt["Longueur (m)"].round(1)
            _xt.rename(columns={"cm_support": "Type de support", "domaine": "Domaine"}, inplace=True)
            st.dataframe(_xt, use_container_width=True, hide_index=True, height=380)

            # Anomalies potentielles
            EXPECTED_PUBLIC  = ["Souterrain RIP construit", "Souterrain RIP RAF",
                                "Aérien Enedis", "Aérien Orange", "Aérien RIP",
                                "Chambre", "Aéro-souterrain", "Aéro-souterrain Orange"]
            EXPECTED_PRIVATE = ["Façade", "Réseau en parcelle agricole",
                                "Souterrain Orange", "Souterrain Tiers"]
            _anom_details = []
            for _, row in _xt.iterrows():
                sup, dom = row["Type de support"], row["Domaine"]
                n_tr = int(row.get("Tronçons", 0))
                if sup in EXPECTED_PUBLIC and dom != "Public":
                    _anom_details.append({"support": sup, "domaine": dom, "attendu": "Public",  "n": n_tr})
                if sup in EXPECTED_PRIVATE and dom == "Public":
                    _anom_details.append({"support": sup, "domaine": dom, "attendu": "Privé", "n": n_tr})

            if _anom_details:
                st.warning(f" {len(_anom_details)} anomalie(s) de classification détectée(s) - cliquez pour voir les tronçons sur la carte")
                for _ad in _anom_details:
                    _label = f" {_ad['support']} - classé '{_ad['domaine']}' (attendu : {_ad['attendu']}) · {_ad['n']} tronçons"
                    with st.expander(_label):
                        # Tableau des tronçons concernés
                        _anom_rows = _q_full[
                            (_q_full.get("cm_support", pd.Series()) == _ad["support"]) &
                            (_q_full.get("domaine",    pd.Series()) == _ad["domaine"])
                        ] if "cm_support" in _q_full.columns and "domaine" in _q_full.columns else pd.DataFrame()
                        if len(_anom_rows) > 0:
                            _cols_s = [c for c in ["commune","domaine","cm_support","longueur"] if c in _anom_rows.columns]
                            st.dataframe(_anom_rows[_cols_s].head(100), hide_index=True,
                                         use_container_width=True)

                        # Mini-carte folium rouge
                        _feats_a = []
                        for _gj_key in ["pub_voiries", "priv_voiries"]:
                            _gj_src = gjs.get(_gj_key)
                            if _gj_src:
                                _feats_a += [
                                    f for f in _gj_src["features"]
                                    if f["properties"].get("cm_support") == _ad["support"]
                                    and f["properties"].get("domaine") == _ad["domaine"]
                                ]
                        if _feats_a:
                            _gj_a = {"type": "FeatureCollection", "features": _feats_a}
                            _m_a = folium.Map(location=center, zoom_start=12, tiles=None)
                            folium.TileLayer(
                                tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
                                attr="© CARTO", name="Dark", max_zoom=19
                            ).add_to(_m_a)
                            _tt_fields = [x for x in ["commune","cm_support","domaine","longueur"]
                                          if x in (_feats_a[0]["properties"] if _feats_a else {})]
                            GeoJson(
                                _gj_a,
                                name="Anomalies",
                                style_function=lambda f: {"color": "#ff3030","weight": 3.5,"opacity": 1.0},
                                tooltip=GeoJsonTooltip(
                                    fields=_tt_fields,
                                    aliases=[TT_ALIASES.get(f, f+":") for f in _tt_fields],
                                    sticky=False, style=TT_STYLE
                                ) if _tt_fields else None,
                            ).add_to(_m_a)
                            _map_key = f"anom_{_ad['support'][:15]}_{_ad['domaine'][:5]}"
                            st_folium(_m_a, height=320, use_container_width=True,
                                      returned_objects=[], key=_map_key)
                        else:
                            st.info("Tronçons non localisés dans le GeoJSON.")
            else:
                st.success(" Aucune anomalie de classification détectée")
    else:
        st.info("Aucune donnée chargée")
