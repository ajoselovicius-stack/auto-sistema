import sqlite3
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

import streamlit as st

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
                aprasymas TEXT
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
    with st.form("prideti"):
        col1, col2 = st.columns(2)
        with col1:
            marke = st.text_input("Markė *")
            modelis = st.text_input("Modelis *")
            metai = st.number_input("Metai", min_value=1950, max_value=2035, value=2020)
            rida = st.number_input("Rida (km)", min_value=0, value=100000)
        with col2:
            kaina = st.number_input("Kaina (€)", min_value=0.0, value=10000.0)
            vin = st.text_input("VIN")
            aprasymas = st.text_area("Aprašymas")
        if st.form_submit_button("Išsaugoti automobilį"):
            if not marke.strip() or not modelis.strip():
                st.error("Įrašyk markę ir modelį.")
            else:
                with prisijungti() as conn:
                    conn.execute("""
                        INSERT INTO automobiliai (marke, modelis, metai, rida, kaina, vin, aprasymas)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (marke.strip(), modelis.strip(), int(metai), int(rida), float(kaina), vin.strip(), aprasymas.strip()))
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
        if st.form_submit_button("💾 Išsaugoti pakeitimus"):
            if not nauja_marke.strip() or not naujas_modelis.strip():
                st.error("Markė ir modelis privalomi.")
            else:
                with prisijungti() as conn:
                    conn.execute("""
                        UPDATE automobiliai SET marke=?, modelis=?, metai=?, rida=?, kaina=?, vin=?, aprasymas=?
                        WHERE id=?
                    """, (nauja_marke.strip(), naujas_modelis.strip(), int(nauji_metai), int(nauja_rida), float(nauja_kaina), naujas_vin.strip(), naujas_aprasymas.strip(), auto_id))
                st.success("Pakeitimai išsaugoti!")
                st.rerun()
else:
    st.info("Automobilių nerasta. Gali pridėti automobilį aukščiau.")
