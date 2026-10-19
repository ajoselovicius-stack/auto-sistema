import sqlite3
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

import streamlit as st
@st.cache_data(ttl=3600)
def gauti_autoplius_markes():
    import urllib.request

    url = "https://autoplius.lt/importhandler?datacollector=1&category_id=2"
    uzklausa = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(uzklausa, timeout=20) as atsakymas:
        medis = ET.fromstring(atsakymas.read())

    skyrius = medis.find("./response/make_id")
    if skyrius is None:
        return []

    rezultatai = []

    for elementas in skyrius.findall("item"):
        id_elementas = elementas.find("id")
        pavadinimas = elementas.findtext("title")

        if id_elementas is not None and pavadinimas:
            rezultatai.append(
                (pavadinimas.strip(), int(id_elementas.text))
            )

    return sorted(rezultatai, key=lambda x: x[0].lower())


@st.cache_data(ttl=3600)
def gauti_autoplius_modelius(markes_id):
    import urllib.request

    url = (
        "https://autoplius.lt/importhandler"
        f"?datacollector=1&category_id=2&make_id={markes_id}"
    )

    uzklausa = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(uzklausa, timeout=20) as atsakymas:
        medis = ET.fromstring(atsakymas.read())

    skyrius = medis.find("./response/models")
    if skyrius is None:
        return []

    rezultatai = []

    for elementas in skyrius.findall("item"):
        id_elementas = elementas.find("id")
        pavadinimas = elementas.findtext("title")

        if id_elementas is not None and pavadinimas:
            rezultatai.append(
                (pavadinimas.strip(), int(id_elementas.text))
            )

    return sorted(rezultatai, key=lambda x: x[0].lower())
DB_PATH = Path(__file__).with_name("automobiliai.db")
PHOTO_DIR = Path(__file__).with_name("nuotraukos")
PHOTO_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title="AutoSistema", page_icon="🚗", layout="wide")


def prisijungti():
    return sqlite3.connect(DB_PATH)



def sukurti_duomenu_baze():
    with prisijungti() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS automobiliai (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                marke TEXT NOT NULL,
                modelis TEXT NOT NULL,
                metai INTEGER NOT NULL,
                rida INTEGER NOT NULL,
                kaina REAL NOT NULL,
                vin TEXT,
                aprasymas TEXT,
                autoplius_make_id INTEGER,
                autoplius_model_id INTEGER,
                variklio_turis INTEGER,
                kebulo_tipas_id INTEGER,
                galia INTEGER,
                kuro_tipas_id INTEGER,
                pavaru_deze_id INTEGER,
                duru_skaicius_id INTEGER,
                spalva_id INTEGER,
                miestas_id INTEGER,
                pazeidimu_id INTEGER,
                vairo_puse_id INTEGER
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS automobilio_nuotraukos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                automobilio_id INTEGER NOT NULL,
                kelias TEXT NOT NULL,
                FOREIGN KEY (automobilio_id) REFERENCES automobiliai(id)
            )
        """)

        esami_stulpeliai = {
            eilute[1]
            for eilute in conn.execute(
                "PRAGMA table_info(automobiliai)"
            ).fetchall()
        }

        nauji_stulpeliai = {
            "autoplius_make_id": "INTEGER",
            "autoplius_model_id": "INTEGER",
            "variklio_turis": "INTEGER",
            "kebulo_tipas_id": "INTEGER",
            "galia": "INTEGER",
            "kuro_tipas_id": "INTEGER",
            "pavaru_deze_id": "INTEGER",
            "duru_skaicius_id": "INTEGER",
            "spalva_id": "INTEGER",
            "miestas_id": "INTEGER",
            "pazeidimu_id": "INTEGER",
            "vairo_puse_id": "INTEGER"
        }

        for stulpelis, tipas in nauji_stulpeliai.items():
            if stulpelis not in esami_stulpeliai:
                conn.execute(
                    f"ALTER TABLE automobiliai "
                    f"ADD COLUMN {stulpelis} {tipas}"
                )


def gauti_automobilius():
    with prisijungti() as conn:
        return conn.execute("""
            SELECT id, marke, modelis, metai, rida, kaina, vin, aprasymas
            FROM automobiliai ORDER BY id DESC
        """).fetchall()


def gauti_nuotraukas(automobilio_id):
    with prisijungti() as conn:
        return conn.execute("""
            SELECT id, kelias FROM automobilio_nuotraukos
            WHERE automobilio_id = ? ORDER BY id
        """, (automobilio_id,)).fetchall()


def sukurti_xml(automobiliai):
    """Sukuria bendrinį XML eksportą, ne oficialų Autoplius importo failą."""
    saknis = ET.Element("automobiliai", {"formatas": "AutoSistema", "versija": "1.0"})
    for auto in automobiliai:
        auto_id, marke, modelis, metai, rida, kaina, vin, aprasymas = auto
        elementas = ET.SubElement(saknis, "automobilis")
        laukai = {
            "id": auto_id,
            "marke": marke or "",
            "modelis": modelis or "",
            "metai": metai,
            "rida_km": rida,
            "kaina_eur": f"{float(kaina):.2f}",
            "vin": vin or "",
            "aprasymas": aprasymas or "",
        }
        for pavadinimas, reiksme in laukai.items():
            ET.SubElement(elementas, pavadinimas).text = str(reiksme)

        foto_elementas = ET.SubElement(elementas, "nuotraukos")
        for _, kelias in gauti_nuotraukas(auto_id):
            foto_kelias = Path(kelias)
            if foto_kelias.exists():
                # Vietinis kelias naudingas archyvui, bet nėra vieša nuotraukos URL nuoroda.
                ET.SubElement(foto_elementas, "nuotrauka").text = str(foto_kelias)

    ET.indent(saknis, space="  ")
    return ET.tostring(saknis, encoding="utf-8", xml_declaration=True)


sukurti_duomenu_baze()
st.title("🚗 AutoSistema")
st.caption("Automobilių prekybos valdymas")

automobiliai = gauti_automobilius()
c1, c2, c3 = st.columns(3)
c1.metric("Viso automobilių", len(automobiliai))
c2.metric("Bendra vertė", f"{sum(a[5] for a in automobiliai):,.2f} €")
c3.metric("Vidutinė kaina", f"{sum(a[5] for a in automobiliai) / len(automobiliai):,.2f} €" if automobiliai else "0 €")

st.divider()
st.subheader("📤 XML eksportas")
if automobiliai:
    st.download_button(
        "Atsisiųsti automobilius XML formatu",
        data=sukurti_xml(automobiliai),
        file_name="automobiliai.xml",
        mime="application/xml",
    )
    st.caption("Tai bendrinis AutoSistema XML. Prieš importuojant į Autoplius, struktūrą reikės suderinti su jų oficialiais reikalavimais. Vietiniai nuotraukų keliai nėra viešos nuotraukų nuorodos.")
else:
    st.info("XML eksportui pirmiausia pridėk bent vieną automobilį.")

st.divider()

with st.expander("➕ Pridėti automobilį"):

    markiu_sarasas = gauti_autoplius_markes()
    markes = {pavadinimas: markes_id for pavadinimas, markes_id in markiu_sarasas}

    if not markiu_sarasas:
        st.error("Nepavyko užkrauti Autoplius markių katalogo.")
        st.stop()

    pradine_marke = next(
        (pavadinimas for pavadinimas, markes_id in markiu_sarasas if markes_id == 97),
        markiu_sarasas[0][0]
    )

    marke = st.selectbox(
        "Markė *",
        list(markes.keys()),
        index=list(markes.keys()).index(pradine_marke),
        key="prideti_marke"
    )
    autoplius_make_id = markes[marke]

    modeliu_sarasas = gauti_autoplius_modelius(autoplius_make_id)

    if not modeliu_sarasas:
        st.error("Nepavyko užkrauti pasirinktos markės modelių.")
        st.stop()

    modeliai = {pavadinimas: modelio_id for pavadinimas, modelio_id in modeliu_sarasas}
    pradinis_modelis = next(
        (pavadinimas for pavadinimas, modelio_id in modeliu_sarasas if modelio_id == 10941),
        modeliu_sarasas[0][0]
    )

    modelis = st.selectbox(
        "Modelis *",
        list(modeliai.keys()),
        index=list(modeliai.keys()).index(pradinis_modelis),
        key=f"prideti_modelis_{autoplius_make_id}"
    )
    autoplius_model_id = modeliai[modelis]

    with st.form("prideti"):
        col1, col2 = st.columns(2)

        with col1:
            metai = st.number_input("Metai", min_value=1950, max_value=2035, value=2020)
            rida = st.number_input("Rida (km)", min_value=0, value=100000)

        with col2:
            kaina = st.number_input("Kaina (€)", min_value=0.0, value=10000.0)
            vin = st.text_input("VIN")
            aprasymas = st.text_area("Aprašymas")

        st.subheader("Autoplius duomenys")
        col3, col4 = st.columns(2)

        with col3:
            variklio_turis = st.number_input(
                "Variklio tūris (cm³)", min_value=0, value=1995
            )
            kebulo_tipas_id = st.selectbox(
                "Kėbulo tipas",
                options=[4, 5, 7, 2, 1, 3, 6, 9, 10, 8],
                format_func=lambda x: {
                    4: "Sedanas", 5: "Universalas", 7: "SUV",
                    2: "Hečbekas", 1: "Kupė", 3: "Kabrioletas",
                    6: "Minivenas", 9: "Komercinis",
                    10: "Pikapas", 8: "Kita"
                }[x]
            )
            galia = st.number_input("Galia (kW)", min_value=0, value=140)

        with col4:
            kuro_tipas_id = st.selectbox(
                "Kuro tipas",
                options=[32, 30, 35, 31, 36, 33, 17378],
                format_func=lambda x: {
                    32: "Dyzelinas", 30: "Benzinas", 35: "Elektra",
                    31: "Benzinas / LPG", 36: "Benzinas / elektra",
                    33: "Kita", 17378: "Dyzelinas / elektra"
                }[x]
            )
            pavaru_deze_id = st.selectbox(
                "Pavarų dėžė",
                options=[38, 37],
                format_func=lambda x: {38: "Automatinė", 37: "Mechaninė"}[x]
            )
            duru_skaicius_id = st.selectbox(
                "Durų skaičius",
                options=[127, 126, 128],
                format_func=lambda x: {
                    127: "4/5", 126: "2/3", 128: "Kita"
                }[x]
            )
            spalva_id = st.selectbox(
                "Spalva",
                options=[18930, 18931, 18933, 18938, 18937, 18932, 18934, 18935, 18936, 18939, 18929],
                format_func=lambda x: {
                    18930: "Juoda", 18931: "Mėlyna", 18933: "Pilka / sidabrinė",
                    18938: "Balta", 18937: "Raudona", 18932: "Ruda / smėlio",
                    18934: "Žalia", 18935: "Oranžinė", 18936: "Violetinė",
                    18939: "Geltona / auksinė", 18929: "Kita"
                }[x]
            )
            miestas_id = st.selectbox(
                "Miestas",
                options=[1, 2, 3, 4, 5],
                format_func=lambda x: {
                    1: "Vilnius", 2: "Kaunas", 3: "Klaipėda",
                    4: "Šiauliai", 5: "Panevėžys"
                }[x]
            )
            pazeidimu_id = st.selectbox(
                "Pažeidimai",
                options=[10924, 10925],
                format_func=lambda x: {
                    10924: "Be defektų", 10925: "Pažeistas"
                }[x]
            )
            vairo_puse_id = st.selectbox(
                "Vairo pusė",
                options=[10922, 10921],
                format_func=lambda x: {
                    10922: "Kairėje", 10921: "Dešinėje"
                }[x]
            )

        if st.form_submit_button("Išsaugoti automobilį"):
            if not marke.strip() or not modelis.strip():
                st.error("Įrašyk markę ir modelį.")
            else:
                with prisijungti() as conn:
                    conn.execute("""
                        INSERT INTO automobiliai (
                            marke, modelis, metai, rida, kaina, vin, aprasymas,
                            autoplius_make_id, autoplius_model_id, variklio_turis,
                            kebulo_tipas_id, galia, kuro_tipas_id, pavaru_deze_id,
                            duru_skaicius_id, spalva_id, miestas_id,
                            pazeidimu_id, vairo_puse_id
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        marke.strip(), modelis.strip(), int(metai), int(rida),
                        float(kaina), vin.strip(), aprasymas.strip(),
                        int(autoplius_make_id), int(autoplius_model_id),
                        int(variklio_turis), int(kebulo_tipas_id), int(galia),
                        int(kuro_tipas_id), int(pavaru_deze_id),
                        int(duru_skaicius_id), int(spalva_id), int(miestas_id),
                        int(pazeidimu_id), int(vairo_puse_id)
                    ))
                st.success("Automobilis išsaugotas!")
                st.rerun()



st.subheader("📋 Automobilių sąrašas")
paieska = st.text_input("🔎 Ieškoti pagal markę, modelį arba VIN")
filtruoti = [a for a in gauti_automobilius() if paieska.lower() in f"{a[1]} {a[2]} {a[6] or ''}".lower()]

if filtruoti:
    st.dataframe([
        {"ID": a[0], "Markė": a[1], "Modelis": a[2], "Metai": a[3], "Rida (km)": a[4], "Kaina (€)": a[5], "VIN": a[6]}
        for a in filtruoti
    ], use_container_width=True, hide_index=True)

    pasirinkimai = {f"ID {a[0]} – {a[1]} {a[2]} ({a[3]})": a for a in filtruoti}
    st.divider()
    st.subheader("🚘 Automobilio kortelė")
    pavadinimas = st.selectbox("Pasirink automobilį kortelei, nuotraukoms ir redagavimui", list(pasirinkimai.keys()), key="pasirinktas_auto")
    auto = pasirinkimai[pavadinimas]
    auto_id = auto[0]

    kortele_kol, nuotrauku_kol = st.columns([1, 1.4])
    with kortele_kol:
        st.markdown(f"### {auto[1]} {auto[2]}")
        st.caption(f"Automobilio ID: {auto[0]}")
        st.metric("Kaina", f"{auto[5]:,.2f} €")
        st.write(f"**Metai:** {auto[3]}")
        st.write(f"**Rida:** {auto[4]:,} km")
        st.write(f"**VIN:** {auto[6] or 'Nenurodytas'}")
        st.write("**Aprašymas:**")
        st.write(auto[7] or "Aprašymas dar neįrašytas.")

    nuotraukos = gauti_nuotraukas(auto_id)
    with nuotrauku_kol:
        st.markdown("#### 🖼️ Automobilio nuotraukos")
        if nuotraukos:
            st.caption(f"Išsaugota nuotraukų: {len(nuotraukos)}")
            foto_stulpeliai = st.columns(2)
            for i, (foto_id, kelias) in enumerate(nuotraukos):
                foto_kelias = Path(kelias)
                with foto_stulpeliai[i % 2]:
                    if foto_kelias.exists():
                        st.image(str(foto_kelias), caption=f"{auto[1]} {auto[2]}", use_container_width=True)
                    else:
                        st.warning("Nuotraukos failas nerastas.")
                    if st.button("Ištrinti nuotrauką", key=f"trinti_foto_{foto_id}"):
                        with prisijungti() as conn:
                            conn.execute("DELETE FROM automobilio_nuotraukos WHERE id = ?", (foto_id,))
                        if foto_kelias.exists():
                            foto_kelias.unlink()
                        st.rerun()
        else:
            st.info("Šis automobilis dar neturi nuotraukų.")

    with st.form("nuotrauku_ikelimas"):
        failai = st.file_uploader("Pridėti automobilio nuotraukas", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True)
        ikelti = st.form_submit_button("Įkelti nuotraukas")
        if ikelti:
            if not failai:
                st.warning("Pirmiausia pasirink bent vieną nuotrauką.")
            else:
                aplankas = PHOTO_DIR / str(auto_id)
                aplankas.mkdir(parents=True, exist_ok=True)
                kiekis = 0
                for failas in failai:
                    galune = Path(failas.name).suffix.lower()
                    if galune not in [".jpg", ".jpeg", ".png", ".webp"]:
                        continue
                    kelias = aplankas / f"{uuid.uuid4().hex}{galune}"
                    kelias.write_bytes(failas.getvalue())
                    with prisijungti() as conn:
                        conn.execute("INSERT INTO automobilio_nuotraukos (automobilio_id, kelias) VALUES (?, ?)", (auto_id, str(kelias)))
                    kiekis += 1
                st.success(f"Įkelta nuotraukų: {kiekis}")
                st.rerun()

    st.divider()

    st.subheader("✏️ Redaguoti automobilį")
    with st.form("redaguoti"):
        col1, col2 = st.columns(2)

        with col1:
            nauja_marke = st.text_input("Markė", value=auto[1])
            naujas_modelis = st.text_input("Modelis", value=auto[2])
            nauji_metai = st.number_input("Metai", min_value=1950, max_value=2035, value=int(auto[3]))
            nauja_rida = st.number_input("Rida (km)", min_value=0, value=int(auto[4]))

        with col2:
            nauja_kaina = st.number_input("Kaina (€)", min_value=0.0, value=float(auto[5]))
            naujas_vin = st.text_input("VIN", value=auto[6] or "")
            naujas_aprasymas = st.text_area("Aprašymas", value=auto[7] or "")


        st.subheader("Autoplius duomenys")

        with prisijungti() as conn:
            papildomi = conn.execute(
                """SELECT autoplius_make_id, autoplius_model_id,
                variklio_turis, kebulo_tipas_id, galia, kuro_tipas_id,
                pavaru_deze_id, duru_skaicius_id, spalva_id, miestas_id,
                pazeidimu_id, vairo_puse_id
                FROM automobiliai WHERE id=?""",
                (auto_id,)
            ).fetchone()

        def esama(indeksas, numatytoji):
            if papildomi and papildomi[indeksas] is not None:
                return int(papildomi[indeksas])
            return numatytoji


        markiu_sarasas = gauti_autoplius_markes()

        if not markiu_sarasas:
            st.error("Nepavyko gauti markių iš Autoplius. Patikrink interneto ryšį.")
            markiu_sarasas = [(auto[1], esama(0, 97))]

        markes = {pavadinimas: markes_id for pavadinimas, markes_id in markiu_sarasas}

        esama_markes_id = esama(0, 97)
        esama_markes_pavadinimas = next(
            (pavadinimas for pavadinimas, markes_id in markiu_sarasas
             if markes_id == esama_markes_id),
            None
        )

        if esama_markes_pavadinimas is None:
            esama_markes_pavadinimas = next(
                (pavadinimas for pavadinimas in markes
                 if pavadinimas.casefold() == str(auto[1]).casefold()),
                markiu_sarasas[0][0]
            )

        naujas_make_pavadinimas = st.selectbox(
            "Markė",
            list(markes.keys()),
            index=list(markes.keys()).index(esama_markes_pavadinimas),
            key=f"redaguoti_marke_{auto_id}"
        )
        naujas_make_id = markes[naujas_make_pavadinimas]

        modeliu_sarasas = gauti_autoplius_modelius(naujas_make_id)

        if not modeliu_sarasas:
            st.warning("Šios markės modelių katalogo gauti nepavyko.")
            modeliu_sarasas = [(auto[2], esama(1, 10941))]

        modeliai = {pavadinimas: modelio_id for pavadinimas, modelio_id in modeliu_sarasas}

        esamas_modelio_id = esama(1, 10941)
        esamas_modelio_pavadinimas = next(
            (pavadinimas for pavadinimas, modelio_id in modeliu_sarasas
             if modelio_id == esamas_modelio_id),
            None
        )

        if esamas_modelio_pavadinimas is None:
            esamas_modelio_pavadinimas = next(
                (pavadinimas for pavadinimas in modeliai
                 if pavadinimas.casefold() == str(auto[2]).casefold()),
                modeliu_sarasas[0][0]
            )

        naujas_modelio_pavadinimas = st.selectbox(
            "Modelis",
            list(modeliai.keys()),
            index=list(modeliai.keys()).index(esamas_modelio_pavadinimas),
            key=f"redaguoti_modelis_{auto_id}"
        )
        naujas_model_id = modeliai[naujas_modelio_pavadinimas]


        c3, c4 = st.columns(2)

        with c3:
            naujas_variklio_turis = st.number_input(
                "Variklio tūris (cm³)", min_value=0,
                value=esama(2, 1995)
            )

            kebulai = {
                "Kupė": 1,
                "Hečbekas": 2,
                "Kabrioletas": 3,
                "Sedanas": 4,
                "Universalus": 5,
                "Vienatūris": 6,
                "SUV / visureigis": 7,
                "Kitas": 8,
                "Komercinis": 9,
                "Pikapas": 10
            }
            kebulo_id = esama(3, 4)
            kebulo_atvirksciai = {v: k for k, v in kebulai.items()}
            kebulo_pasirinkimas = st.selectbox(
                "Kėbulo tipas",
                list(kebulai.keys()),
                index=list(kebulai.keys()).index(
                    kebulo_atvirksciai[kebulo_id]
                ) if kebulo_id in kebulo_atvirksciai else 3
            )
            naujas_kebulo_id = kebulai[kebulo_pasirinkimas]

            nauja_galia = st.number_input(
                "Galia (kW)", min_value=0, value=140
            )

            degalai = {
                "Benzinas": 30,
                "Benzinas / LPG": 31,
                "Dyzelinas": 32,
                "Kiti degalai": 33,
                "Elektra": 35,
                "Benzinas / elektra (hibridas)": 36,
                "Dyzelinas / elektra (hibridas)": 17378
            }
            kuro_id = esama(5, 32)
            kuro_atvirksciai = {v: k for k, v in degalai.items()}
            kuro_pasirinkimas = st.selectbox(
                "Kuro tipas",
                list(degalai.keys()),
                index=list(degalai.keys()).index(
                    kuro_atvirksciai[kuro_id]
                ) if kuro_id in kuro_atvirksciai else 2
            )
            naujas_kuro_id = degalai[kuro_pasirinkimas]

            dezes = {"Mechaninė": 37, "Automatinė": 38}
            deze_id = esama(6, 38)
            deze_atvirksciai = {v: k for k, v in dezes.items()}
            deze_pasirinkimas = st.selectbox(
                "Pavarų dėžė",
                list(dezes.keys()),
                index=list(dezes.keys()).index(
                    deze_atvirksciai[deze_id]
                ) if deze_id in deze_atvirksciai else 1
            )
            nauja_deze_id = dezes[deze_pasirinkimas]

        with c4:
            durys = {
                "2 arba 3 durys": 126,
                "4 arba 5 durys": 127,
                "Kita": 128
            }
            duru_id = esama(7, 127)
            duru_atvirksciai = {v: k for k, v in durys.items()}
            duru_pasirinkimas = st.selectbox(
                "Durų skaičius",
                list(durys.keys()),
                index=list(durys.keys()).index(
                    duru_atvirksciai[duru_id]
                ) if duru_id in duru_atvirksciai else 1
            )
            naujos_durys_id = durys[duru_pasirinkimas]

            spalvos = {
                "Juoda": 18930,
                "Mėlyna": 18931,
                "Ruda / smėlio": 18932,
                "Pilka / sidabrinė": 18933,
                "Žalia": 18934,
                "Oranžinė": 18935,
                "Violetinė": 18936,
                "Raudona": 18937,
                "Balta": 18938,
                "Geltona / auksinė": 18939,
                "Kita": 18929
            }
            spalvos_id = esama(8, 18930)
            spalvos_atvirksciai = {v: k for k, v in spalvos.items()}
            spalvos_pasirinkimas = st.selectbox(
                "Spalva",
                list(spalvos.keys()),
                index=list(spalvos.keys()).index(
                    spalvos_atvirksciai[spalvos_id]
                ) if spalvos_id in spalvos_atvirksciai else 0
            )
            nauja_spalva_id = spalvos[spalvos_pasirinkimas]

            miestai = {
                "Vilnius": 1,
                "Kaunas": 2,
                "Klaipėda": 3,
                "Šiauliai": 4,
                "Panevėžys": 5
            }
            miesto_id = esama(9, 1)
            miesto_atvirksciai = {v: k for k, v in miestai.items()}
            miesto_pasirinkimas = st.selectbox(
                "Miestas",
                list(miestai.keys()),
                index=list(miestai.keys()).index(
                    miesto_atvirksciai[miesto_id]
                ) if miesto_id in miesto_atvirksciai else 0
            )
            naujas_miestas_id = miestai[miesto_pasirinkimas]

            pazeidimai = {
                "Be defektų": 10924,
                "Apgadintas": 10925,
                "Variklio defektas": 18968,
                "Pavarų dėžės defektas": 18969,
                "Kiti dideli defektai": 18970
            }
            pazeidimu_id = esama(10, 10924)
            pazeidimu_atvirksciai = {v: k for k, v in pazeidimai.items()}
            pazeidimu_pasirinkimas = st.selectbox(
                "Pažeidimų būklė",
                list(pazeidimai.keys()),
                index=list(pazeidimai.keys()).index(
                    pazeidimu_atvirksciai[pazeidimu_id]
                ) if pazeidimu_id in pazeidimu_atvirksciai else 0
            )
            naujas_pazeidimu_id = pazeidimai[pazeidimu_pasirinkimas]

            vairai = {"Kairėje": 10922, "Dešinėje": 10921}
            vairo_id = esama(11, 10922)
            vairo_atvirksciai = {v: k for k, v in vairai.items()}
            vairo_pasirinkimas = st.selectbox(
                "Vairo pusė",
                list(vairai.keys()),
                index=list(vairai.keys()).index(
                    vairo_atvirksciai[vairo_id]
                ) if vairo_id in vairo_atvirksciai else 0
            )
            naujas_vairo_id = vairai[vairo_pasirinkimas]
            if not nauja_marke.strip() or not naujas_modelis.strip():
                st.error("Markė ir modelis privalomi.")
            else:
                with prisijungti() as conn:
                    conn.execute("""
                        UPDATE automobiliai SET
                            marke=?, modelis=?, metai=?, rida=?, kaina=?, vin=?, aprasymas=?,
                            autoplius_make_id=?, autoplius_model_id=?, variklio_turis=?,
                            kebulo_tipas_id=?, galia=?, kuro_tipas_id=?, pavaru_deze_id=?,
                            duru_skaicius_id=?, spalva_id=?, miestas_id=?, pazeidimu_id=?,
                            vairo_puse_id=?
                        WHERE id=?
                    """, (
                        nauja_marke.strip(), naujas_modelis.strip(), int(nauji_metai),
                        int(nauja_rida), float(nauja_kaina), naujas_vin.strip(),
                        naujas_aprasymas.strip(), int(naujas_make_id), int(naujas_model_id),
                        int(naujas_variklio_turis), int(naujas_kebulo_id), int(nauja_galia),
                        int(naujas_kuro_id), int(nauja_deze_id), int(naujos_durys_id),
                        int(nauja_spalva_id), int(naujas_miestas_id),
                        int(naujas_pazeidimu_id), int(naujas_vairo_id), auto_id
                    ))
                st.success("Pakeitimai išsaugoti!")
                st.rerun()
else:
    st.info("Automobilių nerasta. Gali pridėti automobilį aukščiau.")

# ==========================================
# AUTOPLIUS XML EKSPORTAS
# ==========================================

import sqlite3 as xml_sqlite3
import xml.etree.ElementTree as xml_et
from pathlib import Path as XmlPath
import streamlit as xml_st

xml_st.divider()
xml_st.header("XML eksportas į Autoplius")

xml_db_path = XmlPath(__file__).resolve().parent / "automobiliai.db"

try:
    with xml_sqlite3.connect(str(xml_db_path)) as xml_conn:
        xml_conn.row_factory = xml_sqlite3.Row
        xml_cars = xml_conn.execute("""
            SELECT *
            FROM automobiliai
            ORDER BY id DESC
        """).fetchall()

        xml_photo_counts = {
            row["automobilio_id"]: row["kiekis"]
            for row in xml_conn.execute("""
                SELECT automobilio_id, COUNT(*) AS kiekis
                FROM automobilio_nuotraukos
                GROUP BY automobilio_id
            """).fetchall()
        }

    if not xml_cars:
        xml_st.info("Duomenų bazėje automobilių dar nėra.")
    else:
        xml_car_options = {
            (
                f'ID {car["id"]} | '
                f'{car["marke"] or ""} {car["modelis"] or ""} | '
                f'{car["metai"] or ""} | '
                f'{car["kaina"] or ""} €'
            ): car
            for car in xml_cars
        }

        xml_selected_label = xml_st.selectbox(
            "Pasirink automobilį XML failui",
            list(xml_car_options.keys()),
            key="autoplius_xml_car"
        )
        xml_car = xml_car_options[xml_selected_label]

        xml_st.write(
            "Pasirinktas automobilis: "
            f'**{xml_car["marke"] or ""} {xml_car["modelis"] or ""}**'
        )

        xml_missing = []

        if not xml_car["autoplius_make_id"]:
            xml_missing.append("Autoplius markės ID")
        if not xml_car["autoplius_model_id"]:
            xml_missing.append("Autoplius modelio ID")
        if xml_car["kaina"] is None:
            xml_missing.append("Kaina")
        if xml_car["metai"] is None:
            xml_missing.append("Pagaminimo metai")

        if xml_missing:
            xml_st.warning(
                "Trūksta šių duomenų: " + ", ".join(xml_missing)
            )

        xml_st.caption(
            "Nuotraukos: "
            f'{xml_photo_counts.get(xml_car["id"], 0)} vietinių failų. '
            "Jų keliai neįtraukiami, nes Autoplius XML reikia "
            "viešai pasiekiamų nuotraukų URL adresų."
        )

        if xml_st.button("Paruošti Autoplius XML", key="prepare_autoplius_xml"):
            xml_root = xml_et.Element(
                "autoplius",
                {"xmlns:xsi": "https://www.w3.org/2001/XMLSchema-instance"}
            )
            xml_announcements = xml_et.SubElement(xml_root, "announcements")
            xml_car_element = xml_et.SubElement(xml_announcements, "cars")

            xml_fields = [
                ("external_id", xml_car["id"]),
                ("make_id", xml_car["autoplius_make_id"]),
                ("model_id", xml_car["autoplius_model_id"]),
                ("sell_price", xml_car["kaina"]),
                ("comments", xml_car["aprasymas"]),
                ("engine_capacity", xml_car["variklio_turis"]),
                ("body_type_id", xml_car["kebulo_tipas_id"]),
                ("kilometrage", xml_car["rida"]),
                ("power", xml_car["galia"]),
                ("fuel_id", xml_car["kuro_tipas_id"]),
                ("number_of_doors_id", xml_car["duru_skaicius_id"]),
                ("color_id", xml_car["spalva_id"]),
                ("gearbox_id", xml_car["pavaru_deze_id"]),
                ("has_damaged_id", xml_car["pazeidimu_id"]),
                ("steering_wheel_id", xml_car["vairo_puse_id"]),
                ("fk_place_cities_id", xml_car["miestas_id"]),
            ]

            for xml_tag, xml_value in xml_fields:
                if xml_value is not None and str(xml_value).strip():
                    xml_child = xml_et.SubElement(xml_car_element, xml_tag)
                    xml_child.text = str(xml_value).strip()

            if xml_car["metai"] is not None:
                xml_make_date = xml_et.SubElement(
                    xml_car_element, "make_date"
                )
                xml_make_date.text = f'{int(xml_car["metai"]):04d}-01'

            xml_et.indent(xml_root, space="  ")
            xml_content = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                + xml_et.tostring(
                    xml_root, encoding="unicode", short_empty_elements=True
                )
            )

            xml_st.download_button(
                "Atsisiųsti XML failą",
                data=xml_content.encode("utf-8"),
                file_name=f'autoplius_{xml_car["id"]}.xml',
                mime="application/xml",
                key="download_autoplius_xml"
            )

            xml_st.info(
                "XML paruoštas. Prieš įkeliant į Autoplius reikės "
                "patikrinti privalomus laukus, kontaktų duomenis "
                "ir nuotraukų URL adresus."
            )

except Exception as xml_error:
    xml_st.error(
        "Nepavyko paruošti XML. Klaidos informacija: "
        + str(xml_error)
    )
