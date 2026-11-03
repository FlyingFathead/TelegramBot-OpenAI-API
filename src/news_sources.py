"""Publisher sections keyed by the existing Elasticsearch action names."""
from dataclasses import dataclass


@dataclass(frozen=True)
class NewsSource:
    label: str
    rss: str
    page: str
    domains: tuple[str, ...]
    max_days: int = 7


SOURCES = {
    "get_bbc_business": NewsSource(
        "BBC News Business (bbc.co.uk)", "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.bbc.com/business", ('bbc.com', 'bbc.co.uk')),
    "get_bbc_science_environment": NewsSource(
        "BBC News Science & Environment (bbc.co.uk)", "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "https://www.bbc.com/news/science_and_environment", ('bbc.com', 'bbc.co.uk'), 90),
    "get_bbc_top_stories": NewsSource(
        "BBC News, Top Stories (bbc.co.uk)", "https://feeds.bbci.co.uk/news/rss.xml",
        "https://www.bbc.com/news", ('bbc.com', 'bbc.co.uk')),
    "get_cnn_us_news": NewsSource(
        "CNN News, U.S. (cnn.com)", "https://rss.cnn.com/rss/edition_us.rss",
        "https://edition.cnn.com/us", ('cnn.com',)),
    "get_hs_etusivu": NewsSource(
        "Helsingin Sanomat (hs.fi) etusivun uutiset", "https://www.hs.fi/rss/teasers/etusivu.xml",
        "https://www.hs.fi/", ('hs.fi',)),
    "get_hs_uusimmat": NewsSource(
        "Helsingin Sanomat (hs.fi) uusimmat uutiset", "https://www.hs.fi/rss/tuoreimmat.xml",
        "https://www.hs.fi/uusimmat/", ('hs.fi',)),
    "get_hs_kotimaa": NewsSource(
        "Helsingin Sanomat (hs.fi) kotimaan uutiset", "https://www.hs.fi/rss/suomi.xml",
        "https://www.hs.fi/suomi/", ('hs.fi',)),
    "get_hs_ulkomaat": NewsSource(
        "Helsingin Sanomat (hs.fi) ulkomaan uutiset", "https://www.hs.fi/rss/maailma.xml",
        "https://www.hs.fi/maailma/", ('hs.fi',)),
    "get_hs_talous": NewsSource(
        "Helsingin Sanomat (hs.fi) talousuutiset", "https://www.hs.fi/rss/talous.xml",
        "https://www.hs.fi/visio/", ('hs.fi',)),
    "get_hs_politiikka": NewsSource(
        "Helsingin Sanomat (hs.fi) politiikan uutiset", "https://www.hs.fi/rss/politiikka.xml",
        "https://www.hs.fi/politiikka/", ('hs.fi',)),
    "get_hs_helsinki": NewsSource(
        "Helsingin Sanomat (hs.fi) Helsingin uutiset", "https://www.hs.fi/rss/helsinki.xml",
        "https://www.hs.fi/helsinki/", ('hs.fi',)),
    "get_hs_urheilu": NewsSource(
        "Helsingin Sanomat (hs.fi) urheilu-uutiset", "https://www.hs.fi/rss/urheilu.xml",
        "https://www.hs.fi/aihe/urheilu/", ('hs.fi',)),
    "get_hs_kulttuuri": NewsSource(
        "Helsingin Sanomat (hs.fi) kulttuuriuutiset", "https://www.hs.fi/rss/kulttuuri.xml",
        "https://www.hs.fi/kulttuuri/", ('hs.fi',)),
    "get_hs_paakirjoitukset": NewsSource(
        "Helsingin Sanomat (hs.fi) pääkirjoitukset", "https://www.hs.fi/rss/paakirjoitukset.xml",
        "https://www.hs.fi/paakirjoitukset/", ('hs.fi',)),
    "get_hs_lastenuutiset": NewsSource(
        "Helsingin Sanomat (hs.fi) lasten uutiset", "https://www.hs.fi/rss/lastenuutiset.xml",
        "https://www.hs.fi/lastenuutiset/", ('hs.fi',), 365),
    "get_hs_ruoka": NewsSource(
        "Helsingin Sanomat (hs.fi) ruoka", "https://www.hs.fi/rss/ruoka.xml",
        "https://www.hs.fi/ruoka/", ('hs.fi',), 365),
    "get_hs_elama": NewsSource(
        "Helsingin Sanomat (hs.fi) elämä", "https://www.hs.fi/rss/elama.xml",
        "https://www.hs.fi/sivu/hs-elama/", ('hs.fi',), 365),
    "get_hs_tiede": NewsSource(
        "Helsingin Sanomat (hs.fi) tiedeuutiset", "https://www.hs.fi/rss/tiede.xml",
        "https://www.hs.fi/tiede/", ('hs.fi',), 365),
    "get_hs_kuukausiliite": NewsSource(
        "Helsingin Sanomat (hs.fi) kuukausiliite", "https://www.hs.fi/rss/kuukausiliite.xml",
        "https://www.hs.fi/kuukausiliite/", ('hs.fi',), 365),
    "get_il_urheilu": NewsSource(
        "Iltalehti (il.fi) urheilu-uutiset", "https://www.iltalehti.fi/rss/urheilu.xml",
        "https://www.iltalehti.fi/urheilu", ('iltalehti.fi',)),
    "get_is_digitoday": NewsSource(
        "Ilta-Sanomat (is.fi) Digitoday-uutiset", "https://www.is.fi/rss/digitoday.xml",
        "https://www.is.fi/digitoday/", ('is.fi',), 30),
    "get_is_horoskoopit": NewsSource(
        "Ilta-Sanomat (is.fi) horoskoopit", "https://www.is.fi/rss/horoskooppi.xml",
        "https://www.is.fi/menaiset/horoskooppi/", ('is.fi',), 30),
    "get_is_tiede": NewsSource(
        "Ilta-Sanomat (is.fi) tiedeuutiset", "https://www.is.fi/rss/tiede.xml",
        "https://www.is.fi/tiede/", ('is.fi',), 120),
    "get_is_tuoreimmat": NewsSource(
        "Ilta-Sanomat (is.fi), tuoreimmat uutiset", "https://www.is.fi/rss/tuoreimmat.xml",
        "https://www.is.fi/tuoreimmat/", ('is.fi',)),
    "get_is_taloussanomat": NewsSource(
        "Taloussanomat (is.fi/taloussanomat) tuoreimmat", "https://www.is.fi/rss/taloussanomat.xml",
        "https://www.is.fi/taloussanomat/", ('is.fi',)),
    "get_is_ulkomaat": NewsSource(
        "Ilta-Sanomat (is.fi) ulkomaat", "https://www.is.fi/rss/ulkomaat.xml",
        "https://www.is.fi/ulkomaat/", ('is.fi',)),
    "get_is_viihde": NewsSource(
        "Ilta-Sanomat (is.fi) Viihdeuutiset (IS Viihde)", "https://www.is.fi/rss/viihde.xml",
        "https://www.is.fi/viihde/", ('is.fi',)),
    "get_is_kotimaa": NewsSource(
        "Ilta-Sanomat (is.fi) kotimaan uutiset", "https://www.is.fi/rss/kotimaa.xml",
        "https://www.is.fi/kotimaa/", ('is.fi',)),
    "get_is_politiikka": NewsSource(
        "Ilta-Sanomat (is.fi) politiikan uutiset", "https://www.is.fi/rss/politiikka.xml",
        "https://www.is.fi/politiikka/", ('is.fi',)),
    "get_is_paakirjoitus": NewsSource(
        "Ilta-Sanomat (is.fi) pääkirjoitus", "https://www.is.fi/rss/paakirjoitus.xml",
        "https://www.is.fi/paakirjoitus/", ('is.fi',)),
    "get_is_urheilu": NewsSource(
        "Ilta-Sanomat (is.fi) urheilu-uutiset", "https://www.is.fi/rss/urheilu.xml",
        "https://www.is.fi/urheilu/", ('is.fi',)),
    "get_is_tv_ja_elokuvat": NewsSource(
        "Ilta-Sanomat (is.fi) TV & elokuva", "https://www.is.fi/rss/tv-ja-elokuvat.xml",
        "https://www.is.fi/tv-ja-elokuvat/", ('is.fi',), 365),
    "get_is_musiikki": NewsSource(
        "Ilta-Sanomat (is.fi) musiikki", "https://www.is.fi/rss/musiikki.xml",
        "https://www.is.fi/musiikki/", ('is.fi',), 365),
    "get_is_kuninkaalliset": NewsSource(
        "Ilta-Sanomat (is.fi) kuninkaalliset", "https://www.is.fi/rss/kuninkaalliset.xml",
        "https://www.is.fi/kuninkaalliset/", ('is.fi',), 1000),
    "get_is_jaakiekko": NewsSource(
        "Ilta-Sanomat (is.fi) jääkiekko", "https://www.is.fi/rss/jaakiekko.xml",
        "https://www.is.fi/jaakiekko/", ('is.fi',)),
    "get_is_jalkapallo": NewsSource(
        "Ilta-Sanomat (is.fi) jalkapallo", "https://www.is.fi/rss/jalkapallo.xml",
        "https://www.is.fi/jalkapallo/", ('is.fi',)),
    "get_is_ralli": NewsSource(
        "Ilta-Sanomat (is.fi) ralli", "https://www.is.fi/rss/ralli.xml",
        "https://www.is.fi/ralli/", ('is.fi',), 1000),
    "get_is_yleisurheilu": NewsSource(
        "Ilta-Sanomat (is.fi) yleisurheilu", "https://www.is.fi/rss/yleisurheilu.xml",
        "https://www.is.fi/yleisurheilu/", ('is.fi',)),
    "get_is_hiihto": NewsSource(
        "Ilta-Sanomat (is.fi) hiihto", "https://www.is.fi/rss/hiihtolajit.xml",
        "https://www.is.fi/hiihtolajit/", ('is.fi',), 1000),
    "get_is_formula1": NewsSource(
        "Ilta-Sanomat (is.fi) formula 1", "https://www.is.fi/rss/formula1.xml",
        "https://www.is.fi/formula1/", ('is.fi',), 1000),
    "get_is_ravit": NewsSource(
        "Ilta-Sanomat (is.fi) ravit", "https://www.is.fi/rss/ravit.xml",
        "https://www.is.fi/ravit/", ('is.fi',), 1000),
    "get_is_esports": NewsSource(
        "Ilta-Sanomat (is.fi) esports", "https://www.is.fi/rss/digitoday/esports.xml",
        "https://www.is.fi/esports/", ('is.fi',), 1000),
    "get_is_autot": NewsSource(
        "Ilta-Sanomat (is.fi) autot", "https://www.is.fi/rss/autot.xml",
        "https://www.is.fi/autot/", ('is.fi',), 1000),
    "get_is_menaiset": NewsSource(
        "Ilta-Sanomat (is.fi) me naiset", "https://www.is.fi/rss/menaiset.xml",
        "https://www.is.fi/menaiset/", ('is.fi',), 365),
    "get_is_hyvaolo": NewsSource(
        "Ilta-Sanomat (is.fi) hyvä olo", "https://www.is.fi/rss/hyvaolo.xml",
        "https://www.is.fi/hyvaolo/", ('is.fi',), 365),
    "get_is_ruokala": NewsSource(
        "Ilta-Sanomat (is.fi) ruokala", "https://www.is.fi/rss/ruokala.xml",
        "https://www.is.fi/ruokala/", ('is.fi',), 365),
    "get_is_asuminen": NewsSource(
        "Ilta-Sanomat (is.fi) asuminen", "https://www.is.fi/rss/asuminen.xml",
        "https://www.is.fi/asuminen/", ('is.fi',), 365),
    "get_is_matkat": NewsSource(
        "Ilta-Sanomat (is.fi) matkat", "https://www.is.fi/rss/matkat.xml",
        "https://www.is.fi/matkat/", ('is.fi',), 365),
    "get_is_perhe": NewsSource(
        "Ilta-Sanomat (is.fi) perhe", "https://www.is.fi/rss/perhe.xml",
        "https://www.is.fi/perhe/", ('is.fi',), 365),
    "get_yle_etela_karjala": NewsSource(
        "YLE (yle.fi) Etelä-Karjala-uutiset", "https://yle.fi/rss/t/18-180490/fi",
        "https://yle.fi/t/18-180490/fi", ('yle.fi',)),
    "get_yle_etela_pohjanmaa": NewsSource(
        "YLE (yle.fi) Etelä-Pohjanmaa-uutiset", "https://yle.fi/rss/t/18-171883/fi",
        "https://yle.fi/t/18-171883/fi", ('yle.fi',)),
    "get_yle_etela_savo": NewsSource(
        "YLE (yle.fi) Etelä-Savon uutiset", "https://yle.fi/rss/t/18-191034/fi",
        "https://yle.fi/t/18-191034/fi", ('yle.fi',)),
    "get_yle_kainuu": NewsSource(
        "YLE (yle.fi) Kainuun uutiset", "https://yle.fi/rss/t/18-178011/fi",
        "https://yle.fi/t/18-178011/fi", ('yle.fi',)),
    "get_yle_kanta_hame": NewsSource(
        "YLE (yle.fi) Kanta-Hämeen uutiset", "https://yle.fi/rss/t/18-195288/fi",
        "https://yle.fi/t/18-195288/fi", ('yle.fi',)),
    "get_yle_karjalakse": NewsSource(
        "YLE (yle.fi) Uudizet karjalakse", "https://yle.fi/rss/t/18-44136/fi",
        "https://yle.fi/t/18-44136/fi", ('yle.fi',), 1000),
    "get_yle_keski_pohjanmaa": NewsSource(
        "YLE (yle.fi) Keski-Pohjanmaan uutiset", "https://yle.fi/rss/t/18-188752/fi",
        "https://yle.fi/t/18-188752/fi", ('yle.fi',)),
    "get_yle_keski_suomi": NewsSource(
        "YLE (yle.fi) Keski-Suomen uutiset", "https://yle.fi/rss/t/18-185882/fi",
        "https://yle.fi/t/18-185882/fi", ('yle.fi',)),
    "get_yle_kotimaa": NewsSource(
        "YLE (yle.fi) kotimaan uutiset", "https://yle.fi/rss/t/18-34837/fi",
        "https://yle.fi/t/18-34837/fi", ('yle.fi',)),
    "get_yle_kulttuuri": NewsSource(
        "YLE (yle.fi) kulttuuriuutiset", "https://yle.fi/rss/t/18-208149/fi",
        "https://yle.fi/kulttuuri", ('yle.fi',)),
    "get_yle_kymenlaakso": NewsSource(
        "YLE (yle.fi) Kymenlaakson uutiset", "https://yle.fi/rss/t/18-198551/fi",
        "https://yle.fi/t/18-198551/fi", ('yle.fi',)),
    "get_yle_lappi": NewsSource(
        "YLE (yle.fi) Lapin uutiset", "https://yle.fi/rss/t/18-148152/fi",
        "https://yle.fi/t/18-148152/fi", ('yle.fi',)),
    "get_yle_latest_news": NewsSource(
        "YLE (yle.fi) tuoreimmat uutiset", "https://yle.fi/rss/uutiset/tuoreimmat",
        "https://yle.fi/tuoreimmat", ('yle.fi',)),
    "get_yle_liikenne": NewsSource(
        "YLE (yle.fi) liikenneuutiset", "https://yle.fi/rss/t/18-217946/fi",
        "https://yle.fi/t/18-217946/fi", ('yle.fi',)),
    "get_yle_luonto": NewsSource(
        "YLE (yle.fi) luontouutiset", "https://yle.fi/rss/t/18-215452/fi",
        "https://yle.fi/t/18-215452/fi", ('yle.fi',)),
    "get_yle_main_news": NewsSource(
        "YLE (yle.fi) pääuutiset", "https://yle.fi/rss/uutiset/paauutiset",
        "https://yle.fi/", ('yle.fi',)),
    "get_yle_media": NewsSource(
        "YLE (yle.fi) mediauutiset", "https://yle.fi/rss/t/18-35057/fi",
        "https://yle.fi/t/18-35057/fi", ('yle.fi',)),
    "get_yle_most_read": NewsSource(
        "YLE (yle.fi) luetuimmat", "https://yle.fi/rss/uutiset/luetuimmat",
        "https://yle.fi/", ('yle.fi',)),
    "get_yle_nakokulmat": NewsSource(
        "YLE (yle.fi) näkökulmat-uutiset", "https://yle.fi/rss/t/18-35381/fi",
        "https://yle.fi/t/18-35381/fi", ('yle.fi',), 365),
    "get_yle_novosti": NewsSource(
        "YLE (yle.fi) Novosti-uutiset", "https://yle.fi/rss/novosti",
        "https://yle.fi/novosti", ('yle.fi',)),
    "get_yle_news": NewsSource(
        "YLE (yle.fi) News", "https://yle.fi/rss/news",
        "https://yle.fi/news", ('yle.fi',)),
    "get_yle_paijat_hame": NewsSource(
        "YLE (yle.fi) Päijät-Hämeen uutiset", "https://yle.fi/rss/t/18-169788/fi",
        "https://yle.fi/t/18-169788/fi", ('yle.fi',)),
    "get_yle_pirkanmaa": NewsSource(
        "YLE (yle.fi) Pirkanmaan uutiset", "https://yle.fi/rss/t/18-173822/fi",
        "https://yle.fi/t/18-173822/fi", ('yle.fi',)),
    "get_yle_pohjanmaa": NewsSource(
        "YLE (yle.fi) Pohjanmaan uutiset", "https://yle.fi/rss/t/18-174627/fi",
        "https://yle.fi/t/18-174627/fi", ('yle.fi',)),
    "get_yle_pohjois_karjala": NewsSource(
        "YLE (yle.fi) Pohjois-Karjalan uutiset", "https://yle.fi/rss/t/18-189791/fi",
        "https://yle.fi/t/18-189791/fi", ('yle.fi',)),
    "get_yle_pohjois_pohjanmaa": NewsSource(
        "YLE (yle.fi) Pohjois-Pohjanmaan uutiset", "https://yle.fi/rss/t/18-198232/fi",
        "https://yle.fi/t/18-198232/fi", ('yle.fi',)),
    "get_yle_pohjois_savo": NewsSource(
        "YLE (yle.fi) Pohjois-Savon uutiset", "https://yle.fi/rss/t/18-181838/fi",
        "https://yle.fi/t/18-181838/fi", ('yle.fi',)),
    "get_yle_sapmi": NewsSource(
        "YLE (yle.fi) Sápmi-uutiset", "https://yle.fi/rss/sapmi",
        "https://yle.fi/sapmi", ('yle.fi',)),
    "get_yle_satakunta": NewsSource(
        "YLE (yle.fi) Satakunnan uutiset", "https://yle.fi/rss/t/18-197394/fi",
        "https://yle.fi/t/18-197394/fi", ('yle.fi',)),
    "get_yle_selkouutiset": NewsSource(
        "YLE (yle.fi) Selkouutiset", "https://yle.fi/rss/selkouutiset",
        "https://yle.fi/selkouutiset/kaikki-lahetykset", ('yle.fi',)),
    "get_yle_tiede": NewsSource(
        "YLE (yle.fi) tiedeuutiset", "https://yle.fi/rss/t/18-212923/fi",
        "https://yle.fi/t/18-212923/fi", ('yle.fi',)),
    "get_yle_terveys": NewsSource(
        "YLE (yle.fi) terveysuutiset", "https://yle.fi/rss/t/18-209306/fi",
        "https://yle.fi/t/18-209306/fi", ('yle.fi',)),
    "get_yle_uusimaa": NewsSource(
        "YLE (yle.fi) Uusimaa", "https://yle.fi/rss/t/18-177980/fi",
        "https://yle.fi/t/18-177980/fi", ('yle.fi',)),
    "get_yle_urheilu": NewsSource(
        "YLE (yle.fi) urheilu-uutiset", "https://yle.fi/rss/urheilu",
        "https://yle.fi/urheilu", ('yle.fi',)),
    "get_yle_varsinais_suomi": NewsSource(
        "YLE (yle.fi) Varsinais-Suomen uutiset", "https://yle.fi/rss/t/18-198259/fi",
        "https://yle.fi/t/18-198259/fi", ('yle.fi',)),
    "get_yle_viihde": NewsSource(
        "YLE (yle.fi) viihdeuutiset", "https://yle.fi/rss/t/18-205614/fi",
        "https://yle.fi/t/18-205614/fi", ('yle.fi',)),
}
