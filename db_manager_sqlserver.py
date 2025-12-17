import pyodbc
import re
from typing import Any, Dict, List, Optional
from datetime import datetime

class DBManager:
    def __init__(self) -> None:
        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=localhost;"
            "DATABASE=TalmaWR;"
            "Trusted_Connection=yes;"
            "TrustServerCertificate=yes;"
        )
        print("Conectando a BD:", conn_str)
        self.conn = pyodbc.connect(conn_str)
        self.conn.autocommit = True
        self._ensure_preingreso_table()

    @staticmethod
    def _rows_to_dicts(cursor) -> List[Dict[str, Any]]:
        cols = [c[0] for c in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    @staticmethod
    def _one_to_dict(cursor) -> Optional[Dict[str, Any]]:
        row = cursor.fetchone()
        if not row: return None
        cols = [c[0] for c in cursor.description]
        return dict(zip(cols, row))

    def _ensure_preingreso_table(self) -> None:
        pass

    def get_aerolineas(self) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT ID_AERO, NOM_AERO FROM Aerolinea ORDER BY ID_AERO")
        return self._rows_to_dicts(cur)

    def insert_pre_ingreso(self, data: Dict[str, Any]) -> None:
        sql = """
        INSERT INTO PreIngreso (
            ID_AERO, NOM_AERO, MAWB, HAWB, CONTENIDO, DESTINO,
            CONSIGNATARIO, EXPORTADOR, AGEN_ADUAN, EMBALAJE,
            NUM_BULTO, PESO, TIPO_CARGA, DIMENSIONES,
            DAM, ANIO_DAM, ADU_NUM,
            FECHA_NUMERACION, FECHA_VEN_ADUANA, REGIMEN, AGEN_CARGA, usuario_id
        )
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """
        params = [
            data.get("id_aero"), data.get("nom_aero"), data.get("mawb"), data.get("hawb"),
            data.get("contenido"), data.get("destino"), data.get("consignatario"),
            data.get("exportador"), data.get("agen_aduan"), data.get("embalaje"),
            data.get("num_bulto"), data.get("peso"), data.get("tipo_carga"),
            data.get("dimensiones"), 
            data.get("dam_num"), 
            data.get("anio_dam"), data.get("aduana_num"), data.get("fecha_numeracion"),
            data.get("fecha_vencimiento"), data.get("regimen"), data.get("agen_carga"),
            data.get("usuario_id"),
        ]
        cur = self.conn.cursor()
        cur.execute(sql, params)

    def search_pre_ingreso(self, mawb=None, hawb=None, incluir_materializados=True) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM PreIngreso WHERE 1 = 1"
        params = []
        if not incluir_materializados:
            sql += " AND (MATERIALIZADO IS NULL OR MATERIALIZADO = 0)"
        if mawb:
            sql += " AND MAWB LIKE ?"; params.append(f"%{mawb}%")
        if hawb:
            sql += " AND HAWB LIKE ?"; params.append(f"%{hawb}%")
        cur = self.conn.cursor()
        cur.execute(sql, params)
        return self._rows_to_dicts(cur)

    def update_pre_ingreso_fisicos(self, mawb, hawb, num_bulto, peso, dimensiones):
        sql = "UPDATE PreIngreso SET NUM_BULTO=?, PESO=?, DIMENSIONES=? WHERE MAWB=?"
        params = [num_bulto, peso, dimensiones, mawb]
        if hawb:
            sql += " AND HAWB=?"; params.append(hawb)
        cur = self.conn.cursor()
        cur.execute(sql, params)

    def search_pre_ingreso_recepcion(self, mawb=None, hawb=None, dam=None, fecha_desde=None, fecha_hasta=None, aerolinea=None):
        sql = """
        SELECT p.ID AS cod_war, p.FECHA_REG AS fecha_ini, p.NOM_AERO AS aerolinea,
               p.MAWB, p.HAWB, p.DAM AS n_dam, p.ANIO_DAM, p.REGIMEN, '' AS canal
        FROM PreIngreso p WHERE 1=1
        """
        params = []
        if mawb:
            sql += " AND p.MAWB LIKE ?"; params.append(f"%{mawb}%")
        if hawb:
            sql += " AND p.HAWB LIKE ?"; params.append(f"%{hawb}%")
        if dam:
            sql += " AND p.DAM LIKE ?"; params.append(f"%{dam}%")
        if aerolinea:
            sql += " AND p.NOM_AERO LIKE ?"; params.append(f"%{aerolinea}%")
        if fecha_desde:
            sql += " AND CONVERT(date, p.FECHA_REG) >= CONVERT(date, ?)"; params.append(fecha_desde)
        if fecha_hasta:
            sql += " AND CONVERT(date, p.FECHA_REG) <= CONVERT(date, ?)"; params.append(fecha_hasta)
        
        sql += " ORDER BY p.FECHA_REG DESC"
        cur = self.conn.cursor()
        cur.execute(sql, params)
        return self._rows_to_dicts(cur)

    def get_next_cod_war(self) -> str:
        cur = self.conn.cursor()
        cur.execute("SELECT NEXT VALUE FOR dbo.seq_WR;")
        return f"WR{cur.fetchone()[0]:06d}"

    def search_guias(self, mawb=None, hawb=None, dam=None, fecha_desde=None, fecha_hasta=None, aerolinea=None):
        def _clean(s): return s.replace(" ", "").replace("-", "") if s else None
        mawb, hawb, dam = _clean(mawb), _clean(hawb), _clean(dam)

        sql = """
        SELECT
            wr.COD_WAR AS cod_war, wr.FE_INI_RECEP AS fecha_ini,
            wr.FE_FIN_RECEP AS fecha_fin, 
            wr.COD_CAN AS canal, NULL AS canal_nombre,
            wr.ID_AERO AS cod_aero, a.NOM_AERO AS aerolinea,
            wr.COD_GUI_MA AS mawb, ISNULL(gh.COD_GUIA_HIJA, pre.HAWB) AS hawb,
            ISNULL(wr.N_DAM, pre.DAM) AS n_dam, dam.AN_NUME AS anio_dam,
            dam.RE AS regimen, pre.ID AS pre_id
        FROM WarehouseReceipt wr
        LEFT JOIN Aerolinea a ON a.ID_AERO = wr.ID_AERO
        LEFT JOIN NumeroDAM dam ON dam.N_DAM = wr.N_DAM
        LEFT JOIN GuiaMadre gm ON gm.COD_GUI_MA = wr.COD_GUI_MA
        LEFT JOIN GuiaHija gh ON gh.COD_GUI_MA = gm.COD_GUI_MA
        LEFT JOIN PreIngreso pre ON pre.MAWB = wr.COD_GUI_MA AND pre.MATERIALIZADO = 1
        WHERE 1 = 1
        """
        params = []
        if mawb:
            sql += " AND REPLACE(REPLACE(wr.COD_GUI_MA, ' ', ''), '-', '') = ?"; params.append(mawb)
        if hawb:
            sql += " AND (REPLACE(REPLACE(gh.COD_GUIA_HIJA, ' ', ''), '-', '') = ? OR REPLACE(REPLACE(pre.HAWB, ' ', ''), '-', '') = ?)"; params.extend([hawb, hawb])
        if dam:
            sql += " AND REPLACE(REPLACE(wr.N_DAM, ' ', ''), '-', '') = ?"; params.append(dam)
        if aerolinea:
            sql += " AND a.NOM_AERO LIKE ?"; params.append(f"%{aerolinea}%")
        if fecha_desde:
            sql += " AND CONVERT(date, wr.FE_INI_RECEP) >= CONVERT(date, ?)"; params.append(fecha_desde)
        if fecha_hasta:
            sql += " AND CONVERT(date, wr.FE_INI_RECEP) <= CONVERT(date, ?)"; params.append(fecha_hasta)

        sql += " ORDER BY wr.FE_INI_RECEP DESC"
        cur = self.conn.cursor()
        cur.execute(sql, params)
        return self._rows_to_dicts(cur)

    def materializar_wr_desde_preingreso(self, pre_id: int, usuario_id: int = None) -> str:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM PreIngreso WHERE ID = ?", (pre_id,))
        pre_data = self._one_to_dict(cur)
        if not pre_data: raise ValueError(f"No existe PreIngreso ID {pre_id}")

        cod_war = self.get_next_cod_war()
        
        def _trunc(s, l): return str(s).strip()[:l] if s else None
        
        dims = str(pre_data.get("DIMENSIONES", "")).lower().replace(' ', '').split('x')
        l, a, h = 0.0, 0.0, 0.0
        if len(dims) >= 3:
            try: 
                l = float(dims[0].replace(',', '.'))
                a = float(dims[1].replace(',', '.'))
                h = float(dims[2].replace(',', '.'))
            except: pass
        
        p_vol = (l * a * h / 6000.0) if (l and a and h) else 0

        try:
            cur.execute("INSERT INTO GuiaMadre (COD_GUI_MA, ID_AERO, BUL, K_REC, P_VOL, LARGO, ANCHO, ALTO) VALUES (?,?,?,?,?,?,?,?)",
                        (pre_data.get("MAWB"), pre_data.get("ID_AERO"), pre_data.get("NUM_BULTO"), pre_data.get("PESO"), p_vol, l, a, h))
        except: pass

        ruc_exp = '99999999999'
        exp_raw = str(pre_data.get("EXPORTADOR") or "").strip()
        m = re.search(r"(\d{11})", exp_raw)
        if m: 
            ruc_exp = m.group(1)
        else:
            try:
                cur.execute("SELECT TOP 1 RUC_EXP FROM Exportador WHERE NOM_EXP = ?", (exp_raw,))
                row = cur.fetchone()
                if row: ruc_exp = row[0]
            except: pass

        cod_agen_adu = None
        adu_txt = str(pre_data.get("AGEN_ADUAN") or "").strip()
        if adu_txt:
            m_adu = re.search(r"(\d{11})", adu_txt)
            cod_agen_adu = m_adu.group(1) if m_adu else adu_txt[:10]
            
            cur.execute("SELECT COD_AGEN_ADU FROM AgenteAduanas WHERE COD_AGEN_ADU=?", (cod_agen_adu,))
            if not cur.fetchone():
                try: cur.execute("INSERT INTO AgenteAduanas (COD_AGEN_ADU, NOM_AGEN_ADU) VALUES (?,?)", (cod_agen_adu, adu_txt[:200]))
                except: pass

        n_dam = _trunc(pre_data.get("DAM") or pre_data.get("DAM_NUM"), 20)
        if n_dam:
            cur.execute("SELECT N_DAM FROM NumeroDAM WHERE N_DAM=?", (n_dam,))
            if not cur.fetchone():
                try: cur.execute("INSERT INTO NumeroDAM (N_DAM, RE, AN_NUME, DAM, ZOE_AE) VALUES (?,?,?,?,'235')", 
                                 (n_dam, _trunc(pre_data.get("REGIMEN"), 2) or '40', pre_data.get("ANIO_DAM") or 2025, f"DAM {n_dam}"))
                except: pass

        ruc_ac = None
        if pre_data.get("AGEN_CARGA"):
            cur.execute("SELECT TOP 1 RUC_AGE_CAR FROM AgenteCarga WHERE NOM_AGE_CAR LIKE ?", (f"%{pre_data.get('AGEN_CARGA')}%",))
            row = cur.fetchone()
            if row: ruc_ac = row[0]

        cur.execute("SELECT COD_CIU_ORI FROM CiudadOrigen WHERE COD_CIU_ORI='LIM'")
        if not cur.fetchone():
            try: cur.execute("INSERT INTO CiudadOrigen (COD_CIU_ORI, PA) VALUES ('LIM', 'PERU')")
            except: pass
            
        cur.execute("SELECT COD_CON FROM Condicion WHERE COD_CON='OK'")
        if not cur.fetchone():
            try: cur.execute("INSERT INTO Condicion (COD_CON, TIP_CON) VALUES ('OK', 'BUEN ESTADO')")
            except: pass

        tipo_carga_txt = str(pre_data.get("TIPO_CARGA") or "").upper()
        cod_tip_alma = 'GEN'
        if "PERECIBLE" in tipo_carga_txt: cod_tip_alma = "PER"
        elif "VALORADA" in tipo_carga_txt: cod_tip_alma = "VAL"
        elif "DGR" in tipo_carga_txt: cod_tip_alma = "DGR"
        
        cur.execute("SELECT COD_TIP_ALMA FROM TipoAlmacenaje WHERE COD_TIP_ALMA=?", (cod_tip_alma,))
        if not cur.fetchone():
             try: cur.execute("INSERT INTO TipoAlmacenaje (COD_TIP_ALMA, TIP_ALMA) VALUES (?, ?)", (cod_tip_alma, tipo_carga_txt[:99]))
             except: pass
            
        sql_wr = """
        INSERT INTO WarehouseReceipt (
            COD_WAR, FE_INI_RECEP, FE_FIN_RECEP, ID_AERO, RUC_EXP, COD_CIU_ORI, COD_CIU_DES, 
            COD_CONSIG, RUC_AGE_CAR, COD_TIP_ALMA, COD_CAN, COD_CON, N_DAM, COD_GUI_MA, 
            COD_AGEN_ADU, REGIMEN, BUL_WR, PESO_WR, LARGO_WR, ANCHO_WR, ALTO_WR, VOL_WR, usuario_id
        ) VALUES (
            ?, SYSDATETIME(), DATEADD(hour, 1, SYSDATETIME()), ?, ?, 'LIM', ?, '0001', ?, 
            ?, 'VERDE', 'OK', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """
        params_wr = [
            cod_war, pre_data.get("ID_AERO"), ruc_exp, _trunc(pre_data.get("COD_CIU_DES") or '001', 10),
            ruc_ac, cod_tip_alma, n_dam, pre_data.get("MAWB"), cod_agen_adu, _trunc(pre_data.get("REGIMEN"), 2) or '40',
            pre_data.get("NUM_BULTO"), pre_data.get("PESO"), l, a, h, p_vol, usuario_id
        ]
        
        cur.execute(sql_wr, params_wr)
        cur.execute("UPDATE PreIngreso SET MATERIALIZADO=1 WHERE ID=?", (pre_id,))
        return cod_war

    def get_wr_header(self, cod_war: str) -> Optional[Dict[str, Any]]:
        sql = """
        SELECT wr.COD_WAR AS cod_war, wr.FE_INI_RECEP AS fecha_ini, wr.FE_FIN_RECEP AS fecha_fin,
               wr.ID_AERO AS cod_aero, a.NOM_AERO AS aerolinea, wr.COD_GUI_MA AS mawb,
               gh.COD_GUIA_HIJA AS hawb, wr.N_DAM AS n_dam, dam.AN_NUME AS anio_dam,
               dam.RE AS regimen, dam.ZOE_AE AS zona_ae, dam.DAM AS dam_texto,
               wr.RUC_EXP AS exportador_ruc, e.NOM_EXP AS exportador_nom,
               wr.COD_CONSIG AS consignatario_cod, co.NOM_CONSIG AS consignatario_nom,
               wr.RUC_AGE_CAR AS agente_carga_ruc, ac.NOM_AGE_CAR AS agente_carga_nom,
               wr.COD_AGEN_ADU AS agente_aduana_cod, aa.NOM_AGEN_ADU AS agente_aduana_nom,
               wr.COD_CAN AS canal, can.COL AS canal_nombre,
               wr.COD_TIP_ALMA AS cod_tipo_almacen, ta.TIP_ALMA AS tipo_almacenaje,
               wr.COD_CON AS cod_condicion, cond.TIP_CON AS condicion,
               wr.BUL_WR AS bul_wr, wr.PESO_WR AS peso_wr, wr.VOL_WR AS vol_wr
        FROM WarehouseReceipt wr
        LEFT JOIN Aerolinea a ON a.ID_AERO = wr.ID_AERO
        LEFT JOIN NumeroDAM dam ON dam.N_DAM = wr.N_DAM
        LEFT JOIN Exportador e ON e.RUC_EXP = wr.RUC_EXP
        LEFT JOIN Consignatario co ON co.COD_CONSIG = wr.COD_CONSIG
        LEFT JOIN AgenteCarga ac ON ac.RUC_AGE_CAR = wr.RUC_AGE_CAR
        LEFT JOIN AgenteAduanas aa ON aa.COD_AGEN_ADU = wr.COD_AGEN_ADU
        LEFT JOIN Canal can ON can.COD_CAN = wr.COD_CAN
        LEFT JOIN TipoAlmacenaje ta ON ta.COD_TIP_ALMA = wr.COD_TIP_ALMA
        LEFT JOIN Condicion cond ON cond.COD_CON = wr.COD_CON
        LEFT JOIN GuiaMadre gm ON gm.COD_GUI_MA = wr.COD_GUI_MA
        LEFT JOIN GuiaHija gh ON gh.COD_GUI_MA = gm.COD_GUI_MA
        WHERE wr.COD_WAR = ?
        """
        cur = self.conn.cursor()
        cur.execute(sql, (cod_war,))
        return self._one_to_dict(cur)

    def get_wr_detalle(self, cod_war: str) -> List[Dict[str, Any]]:
        sql = "SELECT ITEM_NRO AS item, BUL AS bultos, LARGO AS largo, ANCHO AS ancho, ALTO AS alto, P_VOL AS p_vol FROM WR_Detalle WHERE COD_WAR=? ORDER BY ITEM_NRO"
        cur = self.conn.cursor()
        cur.execute(sql, (cod_war,))
        return self._rows_to_dicts(cur)