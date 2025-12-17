import sys
from datetime import datetime
from PyQt5.QtCore import QDate

from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QDialog,
    QMessageBox,
    QFileDialog,
    QTableWidgetItem,
    QTabWidget,  
    QAbstractItemView,     
    QLineEdit
)

import xml.etree.ElementTree as ET
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from db_manager_sqlserver import DBManager
from sunat_service import consultar_dam

UI_PRE_INGRESO = "Ui/FORMULARIO_INGRESO.ui"
UI_INGRESO_ALM = "Ui/INGRESO_ALMACEN.ui"
UI_RECEPCION   = "Ui/RECEPCION.ui"
UI_REGISTRO    = "Ui/REGISTRO.ui"
UI_LOGIN       = "Ui/LOGIN.ui"

db = DBManager()


#  1. FORMULARIO DE PRE-INGRESO
class PreIngresoWindow(QMainWindow):

    def __init__(self, usuario_id=None):
        super().__init__()
        uic.loadUi(UI_PRE_INGRESO, self)
        self.usuario_id = usuario_id

        self.resize(1200, 700)

        self.btnVerificarDam.clicked.connect(self.verificar_dam)

        self.btnGuardar.clicked.connect(self.guardar_pre_ingreso)

        try:
            self.btnCerrarSesion.clicked.connect(self.cerrar_sesion)
        except AttributeError:
            pass

        self.cargar_aerolineas()
        self.cmbAerolinea.currentIndexChanged.connect(
            self.actualizar_nombre_aerolinea
        )

    def cargar_aerolineas(self):
        self.cmbAerolinea.clear()
        self.cmbAerolinea.addItem("-- seleccionar --", None)

        aerolineas = db.get_aerolineas()
        for a in aerolineas:
            self.cmbAerolinea.addItem(a["ID_AERO"], a["NOM_AERO"])

        self.txtNombreAerolinea.setText("")

    def actualizar_nombre_aerolinea(self, index: int):
        nom = self.cmbAerolinea.itemData(index)
        if nom is None:
            self.txtNombreAerolinea.clear()
        else:
            self.txtNombreAerolinea.setText(nom)

    def verificar_dam(self):
        dam = self.txtDAM.text().strip()
        if not dam:
            QMessageBox.warning(self, "DAM", "Ingrese un número de DAM primero.")
            return

        try:
            info = consultar_dam(dam)
        except ValueError as e:
            QMessageBox.warning(self, "DAM", str(e))
            return

        idx = self.cboRegimen.findText(info["regimen"])
        if idx >= 0:
            self.cboRegimen.setCurrentIndex(idx)

        self.txtAnioDam.setText(str(info["anio_dam"]))
        self.txtAduanaNum.setText(info["aduana_num"])

        fnum = info["fecha_numeracion"]
        self.dtFechaNumeracion.setDate(QDate(fnum.year, fnum.month, fnum.day))

        if hasattr(self, "dtFechaVencimiento"):
            fven = info["fecha_vencimiento"]
            self.dtFechaVencimiento.setDate(QDate(fven.year, fven.month, fven.day))

        if not self.txtExportador.text().strip():
            self.txtExportador.setText(info["exportador"])
        if not self.txtAgenciaAduanas.text().strip():
            self.txtAgenciaAduanas.setText(info["agencia_aduanas"])

    def guardar_pre_ingreso(self):

        idx_aero = self.cmbAerolinea.currentIndex()
        if idx_aero > 0:
            id_aero = self.cmbAerolinea.currentText().strip()
            nom_aero = self.cmbAerolinea.itemData(idx_aero)
        else:
            id_aero = None
            nom_aero = None

        mawb = self.txtMAWB.text().strip()
        hawb = self.txtHAWB.text().strip()
        contenido = self.txtContenido.text().strip()
        destino = self.txtDestino.text().strip()
        consignatario = self.txtConsignatario.text().strip()
        exportador = self.txtExportador.text().strip()
        agen_aduan = self.txtAgenciaAduanas.text().strip()
        embalaje = self.txtEmbalaje.text().strip()
        ag_carga = self.txtAgenciaCarga.text().strip()

        try:
            agencia_carga = self.txtAgenciaCarga.text().strip()
        except AttributeError:
            agencia_carga = None

        num_bulto_text = self.txtNumBulto.text().strip()
        num_bulto = int(num_bulto_text) if num_bulto_text.isdigit() else None

        peso_text = self.txtPeso.text().strip().replace(",", ".")
        try:
            peso = float(peso_text) if peso_text else None
        except ValueError:
            peso = None

        dam_num = self.txtDAM.text().strip() or None

        texto_regimen = self.cboRegimen.currentText().strip()
        regimen = texto_regimen.split()[0] if texto_regimen else None

        anio_dam_text = self.txtAnioDam.text().strip()
        anio_dam = int(anio_dam_text) if anio_dam_text.isdigit() else None

        aduana_texto = self.txtAduanaNum.text().strip() or None

        if aduana_texto and "-" in aduana_texto:
            aduana_num = aduana_texto.split("-")[0].strip()
        else:
            aduana_num = aduana_texto

        fecha_numeracion = None
        try:
            if self.dtFechaNumeracion and self.dtFechaNumeracion.date().isValid():
                fecha_numeracion = self.dtFechaNumeracion.date().toPyDate()
        except AttributeError:
            pass

        fecha_vencimiento = None
        try:
            if self.dtFechaVencimiento and self.dtFechaVencimiento.date().isValid():
                fecha_vencimiento = self.dtFechaVencimiento.date().toPyDate()
        except AttributeError:
            pass

        tipos = []
        try:
            if self.chkCargaGeneral.isChecked():
                tipos.append("Carga general")
            if self.chkCargaPerecible.isChecked():
                tipos.append("Carga perecible")
            if self.chkCargaCongelada.isChecked():
                tipos.append("Carga congelada")
            if self.chkCargaDGR.isChecked():
                tipos.append("Carga DGR")
            if self.chkCargaFarmaceutica.isChecked():
                tipos.append("Carga farmacéutica")
            if self.chkAOG.isChecked():
                tipos.append("AOG")
            if self.chkRestosHumanos.isChecked():
                tipos.append("Restos humanos")
            if self.chkCourier.isChecked():
                tipos.append("Courier")
            if self.chkAnimalesVivos.isChecked():
                tipos.append("Animales vivos")
            if self.chkCargaValorada.isChecked():
                tipos.append("Carga valorada")
        except AttributeError:
            pass

        tipo_carga_str = ", ".join(tipos) if tipos else None

        campos_obligatorios = [
            (id_aero, "Aerolínea"),
            (mawb, "MAWB"),
            (hawb, "HAWB"),
            (contenido, "Contenido"),
            (destino, "Destino"),
            (consignatario, "Consignatario"),
            (exportador, "Exportador"),
            (agen_aduan, "Agencia de Aduanas"),
            (embalaje, "Embalaje"),
            (num_bulto, "Número de Bultos"),
            (peso, "Peso"),
            (tipo_carga_str, "Tipo de Carga"),
            (ag_carga, "Agencia de Carga"),
            (dam_num, "Número de DAM"),
            (regimen, "Régimen"),
            (anio_dam, "Año DAM"),
            (aduana_num, "Aduana"),
            (fecha_numeracion, "Fecha Numeración"),
        ]

        faltantes = [nombre for valor, nombre in campos_obligatorios if not valor]

        if faltantes:
            QMessageBox.warning(
                self,
                "Guardar",
                "No se puede guardar. Faltan los siguientes datos obligatorios:\n- " + "\n- ".join(faltantes),
            )
            return

        data = {
            "id_aero": id_aero,
            "nom_aero": nom_aero,
            "mawb": mawb,
            "hawb": hawb,
            "contenido": contenido,
            "destino": destino,
            "consignatario": consignatario,
            "exportador": exportador,
            "agen_aduan": agen_aduan,
            "embalaje": embalaje,
            "num_bulto": num_bulto,
            "peso": peso,
            "tipo_carga": tipo_carga_str,
            "agen_carga": ag_carga,
            "dam_num": dam_num,
            "regimen": regimen,
            "anio_dam": anio_dam,
            "aduana_num": aduana_num,
            "fecha_numeracion": fecha_numeracion,
            "fecha_vencimiento": fecha_vencimiento,
            "dimensiones": None,
            "usuario_id": self.usuario_id,
        }

        try:
            db.insert_pre_ingreso(data)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Ocurrió un error al guardar en la BD:\n{e}",
            )
            return

        QMessageBox.information(
            self,
            "Guardar",
            "Datos de pre-ingreso guardados correctamente en la BD.",
        )

    def cerrar_sesion(self):
        reply = QMessageBox.question(
            self,
            "Cerrar Sesión",
            "¿Está seguro de que desea cerrar la sesión?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            import os
            os.execv(sys.executable, [sys.executable] + sys.argv)


#  2. INGRESO ALMACÉN (ACTUALIZACIÓN DE DATOS FÍSICOS)
class IngresoAlmacenWindow(QMainWindow):

    def __init__(self, usuario_id=None):
        super().__init__()
        uic.loadUi(UI_INGRESO_ALM, self)
        self.usuario_id = usuario_id

        self.cboBusqueda.currentIndexChanged.connect(self.limpiar_tabla)
        self.txtBuscar.returnPressed.connect(self.buscar_guias)
        self.btnBuscar.clicked.connect(self.buscar_guias)

        self.tblPendiente.setEditTriggers(QAbstractItemView.NoEditTriggers)

        try:
            self.btnGuardar.clicked.connect(self.guardar_cambios)
        except AttributeError:
            pass

        try:
            self.btnAnadirPesoDimensiones.clicked.connect(self.habilitar_edicion)
        except AttributeError:
            pass

        try:
            self.btnProcesarEnviar.clicked.connect(self.procesar_y_enviar)
        except AttributeError:
            pass

        try:
            self.btnCerrarSesion.clicked.connect(self.cerrar_sesion)
        except AttributeError:
            pass

    def limpiar_tabla(self):
        self.tblPendiente.setRowCount(0)

    def buscar_guias(self):
        tipo = self.cboBusqueda.currentText().strip().upper()
        valor = self.txtBuscar.text().strip()

        if not valor:
            QMessageBox.warning(self, "Búsqueda", "Ingrese una guía para buscar.")
            return

        if tipo == "MAWB":
            guias = db.search_pre_ingreso(mawb=valor)
        else:
            guias = db.search_pre_ingreso(hawb=valor)

        self.tblPendiente.setRowCount(0)

        for g in guias:
            row = self.tblPendiente.rowCount()
            self.tblPendiente.insertRow(row)

            item_mawb = QTableWidgetItem(g.get("MAWB") or "")
            item_mawb.setData(Qt.UserRole, g.get("ID")) 
            self.tblPendiente.setItem(row, 0, item_mawb)
            
            self.tblPendiente.setItem(row, 1, QTableWidgetItem(g.get("HAWB") or ""))

            num_bulto = g.get("NUM_BULTO")
            self.tblPendiente.setItem(
                row, 2,
                QTableWidgetItem("" if num_bulto is None else str(num_bulto))
            )

            peso = g.get("PESO")
            self.tblPendiente.setItem(
                row, 3,
                QTableWidgetItem("" if peso is None else str(peso))
            )

            self.tblPendiente.setItem(
                row, 4,
                QTableWidgetItem(g.get("DIMENSIONES") or "")
            )

            self.tblPendiente.setItem(row, 5, QTableWidgetItem(g.get("NOM_AERO") or ""))
            self.tblPendiente.setItem(row, 6, QTableWidgetItem(g.get("DESTINO") or ""))

        if not guias:
            QMessageBox.information(self, "Búsqueda", "No se encontraron guías.")

    def guardar_cambios(self):
        filas = self.tblPendiente.rowCount()
        if filas == 0:
            QMessageBox.information(self, "Guardar", "No hay filas para guardar.")
            return

        QMessageBox.information(
            self,
            "Guardar",
            f"Se actualizarían los datos físicos de {filas} guía(s). "
            "Cuando tengamos claro el mapeo a TalmaWR, aquí llamaremos a db.update_fisicos().",
        )

    def habilitar_edicion(self):
        self.tblPendiente.setEditTriggers(QAbstractItemView.AllEditTriggers)
        QMessageBox.information(
            self,
            "Edición habilitada",
            "Ahora puedes editar BULTOS, KILOS y DIMENSIONES directamente en la tabla.\n"
            "Luego presiona 'PROCESAR Y ENVIAR' para guardar en la base de datos.",
        )

    def procesar_y_enviar(self):
        filas = self.tblPendiente.rowCount()
        if filas == 0:
            QMessageBox.information(self, "Procesar", "No hay filas para procesar.")
            return

        actualizados = 0
        materializados = 0
        wr_generados = []

        for row in range(filas):
            mawb_item = self.tblPendiente.item(row, 0)
            hawb_item = self.tblPendiente.item(row, 1)
            bultos_item = self.tblPendiente.item(row, 2)
            kilos_item = self.tblPendiente.item(row, 3)
            dim_item = self.tblPendiente.item(row, 4)
            
            pre_id = mawb_item.data(Qt.UserRole) if mawb_item else None

            if not pre_id:
                continue

            mawb = mawb_item.text().strip()
            hawb = hawb_item.text().strip() if hawb_item else ""

            if not mawb:
                continue

            num_bulto = None
            if bultos_item:
                txt_bultos = bultos_item.text().strip()
                if txt_bultos.isdigit():
                    num_bulto = int(txt_bultos)

            peso = None
            if kilos_item:
                txt_peso = kilos_item.text().strip().replace(",", ".")
                try:
                    peso = float(txt_peso) if txt_peso else None
                except ValueError:
                    peso = None

            dimensiones = dim_item.text().strip() if dim_item else None

            try:
                db.update_pre_ingreso_fisicos(
                    mawb=mawb,
                    hawb=hawb or None,
                    num_bulto=num_bulto,
                    peso=peso,
                    dimensiones=dimensiones,
                )
                actualizados += 1
            except Exception as e:
                QMessageBox.warning(self, "Error de Actualización", 
                                    f"Fallo al actualizar datos físicos de MAWB {mawb}:\n{e}")
                continue

            try:
                cod_war = db.materializar_wr_desde_preingreso(pre_id, usuario_id=self.usuario_id)
                materializados += 1
                wr_generados.append(cod_war)
            except Exception as e:
                msg = str(e)
                detalle = None
                low = msg.lower()
                if "ruc_exp" in low or "ruc" in low and ("exp" in low or "export" in low):
                    detalle = (
                        "Error al materializar: posible mapeo incorrecto del campo RUC.\n"
                        "Es probable que el NOMBRE del exportador se esté insertando en la columna RUC_EXP o el valor exceda la longitud permitida.\n"
                        "Revisa el campo 'Exportador' en Pre-Ingreso y la función materializar_wr_desde_preingreso en 'db_manager_sqlserver.py'."
                    )
                elif "truncat" in low or "overflow" in low or "string or binary data" in low:
                    detalle = (
                        "Error de longitud al insertar en la BD: alguno de los campos excede la longitud definida en la columna.\n"
                        "Revisa y/o acorta los valores (Exportador, Agencia, Aerolínea, etc.) o implementa truncamiento en la función de materialización."
                    )

                if detalle:
                    QMessageBox.critical(self, "Error de Materialización", f"{detalle}\n\nError BD:\n{msg}")
                else:
                    QMessageBox.critical(
                        self,
                        "Error de Materialización",
                        f"Fallo crítico al crear Warehouse Receipt para MAWB {mawb}:\n{msg}",
                    )

        self.tblPendiente.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tblPendiente.setRowCount(0) 

        if materializados > 0:
            msg = (
                f"Proceso completado. Se actualizaron {actualizados} registro(s) y "
                f"se **materializaron {materializados} Warehouse Receipts (WR)**:\n"
                f"{', '.join(wr_generados)}"
            )
            QMessageBox.information(self, "Procesar y Enviar", msg)
        else:
            QMessageBox.warning(
                self, 
                "Procesar y Enviar", 
                f"Se actualizaron {actualizados} registros en PreIngreso, "
                "pero **ninguno pudo ser materializado** a Warehouse Receipt."
            )

    def cerrar_sesion(self):
        reply = QMessageBox.question(
            self,
            "Cerrar Sesión",
            "¿Está seguro de que desea cerrar la sesión?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            import os
            os.execv(sys.executable, [sys.executable] + sys.argv)

#  3. RECEPCIÓN (BÚSQUEDA Y SELECCIÓN DE WR)
class RecepcionDialog(QDialog):

    def __init__(self, usuario_id=None, parent=None):
        super().__init__(parent)
        uic.loadUi(UI_RECEPCION, self)
        self.usuario_id = usuario_id

        hoy = QDate.currentDate()
        self.dtFechaFin.setDate(hoy)
        self.dtFechaInicio.setDate(hoy.addMonths(-1))

        self.btnBuscar.clicked.connect(self.buscar)
        self.btnSeleccionar.clicked.connect(self.abrir_registro)

        try:
            self.btnCerrarSesion.clicked.connect(self.cerrar_sesion)
        except AttributeError as e:
            print(f"Error al conectar btnCerrarSesion: {e}")

    def cerrar_sesion(self):
        reply = QMessageBox.question(
            self,
            "Cerrar Sesión",
            "¿Está seguro de que desea cerrar la sesión?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.reject()
            QApplication.quit()
            import os
            os.execv(sys.executable, [sys.executable] + sys.argv)

    def buscar(self):
        guias = []

        fecha_desde = None
        fecha_hasta = None
        linea = None
        mawb = None
        hawb = None
        dam = None

        if self.rbtFecha.isChecked():
            desde = self.dtFechaInicio.date().toString("yyyy-MM-dd")
            hasta = self.dtFechaFin.date().toString("yyyy-MM-dd")

            linea = self.cboLineaAerea.currentText().strip()
            if linea.lower().startswith("[seleccion"):
                linea = None
            guias = db.search_guias(
                fecha_desde=desde,
                fecha_hasta=hasta,
                aerolinea=linea,
            )

        elif self.rbtPorGuia.isChecked():
            tipo = self.cboTipoGuia.currentText().strip().upper()
            nro = self.txtNumeroGuia.text().strip()

            if not nro:
                QMessageBox.warning(self, "Búsqueda", "Ingrese un número de guía.")
                return

            if tipo.startswith("MAWB"):
                mawb = nro
                guias = db.search_guias(mawb=nro)
            else:
                hawb = nro
                guias = db.search_guias(hawb=nro)

        elif self.rbtPorDam.isChecked():
            dam = self.txtNumeroDam.text().strip()
            if not dam:
                QMessageBox.warning(self, "Búsqueda", "Ingrese el número de DAM.")
                return
            guias = db.search_guias(dam=dam)

        else:
            QMessageBox.warning(self, "Búsqueda", "Seleccione una opción de búsqueda.")
            return

        if not guias:
            guias = db.search_pre_ingreso_recepcion(
                mawb=mawb,
                hawb=hawb,
                dam=dam,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                aerolinea=linea,
            )

        self.tblResultados.setRowCount(0)

        for g in guias:
            row = self.tblResultados.rowCount()
            self.tblResultados.insertRow(row)

            n_dam = g.get("n_dam") or ""
            canal = "" 
            aerolinea = g.get("aerolinea") or ""
            mawb_val = g.get("mawb") or ""
            hawb_val = g.get("hawb") or ""
            fecha_ini = str(g.get("fecha_ini") or "")
            
            item_dam = QTableWidgetItem(n_dam)
            item_dam.setData(Qt.UserRole, g.get("cod_war"))
            self.tblResultados.setItem(row, 0, item_dam)

            self.tblResultados.setItem(row, 1, QTableWidgetItem(canal))
            
            self.tblResultados.setItem(row, 2, QTableWidgetItem(aerolinea))
            
            self.tblResultados.setItem(row, 3, QTableWidgetItem(mawb_val))
            
            self.tblResultados.setItem(row, 4, QTableWidgetItem(hawb_val))
            
            self.tblResultados.setItem(row, 5, QTableWidgetItem(aerolinea))
            
            self.tblResultados.setItem(row, 6, QTableWidgetItem(fecha_ini))
            
        if not guias:
            QMessageBox.information(self, "Búsqueda", "No se encontraron resultados.")

    def abrir_registro(self):
        row = self.tblResultados.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selección", "Seleccione una guía en la tabla.")
            return

        item_dam = self.tblResultados.item(row, 0)
        cod_war = item_dam.data(Qt.UserRole) if item_dam else None

        item_mawb = self.tblResultados.item(row, 3)
        mawb = item_mawb.text().strip() if item_mawb else ""

        item_hawb = self.tblResultados.item(row, 4)
        hawb = item_hawb.text().strip() if item_hawb else ""

        item_n_dam = self.tblResultados.item(row, 5)
        n_dam = item_n_dam.text().strip() if item_n_dam else ""
        
        is_pre_ingreso = not (isinstance(cod_war, str) and cod_war.startswith("WR"))

        if is_pre_ingreso and cod_war is not None:
             QMessageBox.warning(self, "Procesamiento", "El documento seleccionado aún está en Pre-Ingreso. Debe ser materializado a WR primero (en la pestaña 'Ingreso Almacén') para generar el XML/PDF.")
             return

        if not (cod_war or (mawb and n_dam)):
            QMessageBox.warning(
                self,
                "Error",
                "No se pudo obtener un identificador válido (COD_WAR o MAWB + DAM).",
            )
            return

        dlg = RegistroAutorizacionDialog(
            cod_war=cod_war,
            mawb=mawb,
            hawb=hawb,
            n_dam=n_dam,
            parent=self,
        )
        dlg.exec_()

#  4. REGISTRO DE AUTORIZACIÓN (XML + PDF WAREHOUSE)
class RegistroAutorizacionDialog(QDialog):

    def __init__(self, cod_war: str, mawb: str, hawb: str, n_dam: str, parent=None):
        super().__init__(parent)
        uic.loadUi(UI_REGISTRO, self)

        self.cod_war = cod_war or None
        self.mawb = mawb
        self.hawb = hawb
        self.n_dam = n_dam

        self.header = None
        self.detalle = []

        self.btnDescargarXML.clicked.connect(self.descargar_xml)
        self.btnDescargarWH.clicked.connect(self.descargar_warehouse_pdf)

        try:
            self.btnTransmitir.clicked.connect(self.transmitir)
        except AttributeError:
            pass

        self.cargar_datos()

    def cargar_datos(self):

        if self.cod_war and isinstance(self.cod_war, str) and self.cod_war.startswith("WR"):
            self.header = db.get_wr_header(self.cod_war)
            self.detalle = db.get_wr_detalle(self.cod_war)

            if self.header:
                self._llenar_formulario_desde_wr()
                return

        pre = db.search_pre_ingreso(mawb=self.mawb, hawb=self.hawb)

        if not pre:
            QMessageBox.critical(
                self,
                "Error",
                "No se encontró información en WarehouseReceipt ni en PreIngreso.",
            )
            return

        pre = pre[0]
        self._llenar_formulario_desde_preingreso(pre)


    def _llenar_formulario_desde_wr(self):
        h = self.header or {}

        self.txtGuiaMadre.setText(h.get("mawb") or "")
        self.txtGuiaHija.setText(h.get("hawb") or "")

        tipo_carga = h.get("tipo_almacenaje") or "GENERAL"
        self.txtTipoCarga.setText(tipo_carga)

        self.txtDescripcion.setText(h.get("dam_texto") or "")
        self.txtBultos.setText(str(h.get("bul_wr") or ""))
        self.txtExportador.setText(h.get("exportador_nom") or "")
        self.txtTipoDocumento.setText("RUC")
        self.txtAgenteCarga.setText(h.get("agente_carga_nom") or "")
        self.txtKilo.setText(str(h.get("peso_wr") or ""))

        self.txtNumeroDam.setText(h.get("n_dam") or "")
        self.txtTipoRegimen.setText(h.get("regimen") or "")
        self.txtAgenciaAduanas.setText(h.get("agente_aduana_nom") or "")

        vol = h.get("vol_wr")

        if (vol is None or vol == 0) and self.detalle:
            vol = self._calcular_volumen_desde_detalle()

        if vol is None or vol == "":
            self.txtVolumen.setText("")
        else:
            self.txtVolumen.setText(f"{float(vol):.3f}")

        mawb = self.txtGuiaMadre.text().strip()
        if mawb:
            try:
                pre_list = db.search_pre_ingreso(mawb=mawb, incluir_materializados=True)
                if pre_list:
                    pre = pre_list[0]
                    if not self.txtGuiaHija.text().strip():
                        self.txtGuiaHija.setText(pre.get("HAWB") or "")
                    if not self.txtDescripcion.text().strip():
                        self.txtDescripcion.setText(pre.get("CONTENIDO") or "")
                    if not self.txtAgenteCarga.text().strip():
                        self.txtAgenteCarga.setText(pre.get("AGEN_CARGA") or "")
                    if not self.txtNumeroDam.text().strip():
                        self.txtNumeroDam.setText(pre.get("DAM_NUM") or pre.get("DAM") or "")
                    if not self.txtTipoRegimen.text().strip():
                        self.txtTipoRegimen.setText(pre.get("REGIMEN") or "")
                    if not self.txtAgenciaAduanas.text().strip():
                        self.txtAgenciaAduanas.setText(pre.get("AGEN_ADUAN") or "")
            except Exception:
                pass

    def _llenar_formulario_desde_preingreso(self, pre: dict):
        self.txtGuiaMadre.setText(pre.get("MAWB") or "")
        self.txtGuiaHija.setText(pre.get("HAWB") or "")

        self.txtTipoCarga.setText(pre.get("TIPO_CARGA") or "")

        self.txtDescripcion.setText(pre.get("CONTENIDO") or "")

        num_bulto = pre.get("NUM_BULTO")
        self.txtBultos.setText("" if num_bulto is None else str(num_bulto))

        self.txtExportador.setText(pre.get("EXPORTADOR") or "")

        self.txtTipoDocumento.setText("RUC")

        self.txtAgenteCarga.setText(pre.get("AGEN_CARGA") or "")

        peso = pre.get("PESO")
        self.txtKilo.setText("" if peso is None else str(peso))

        self.txtNumeroDam.setText(pre.get("DAM") or "")
        self.txtTipoRegimen.setText(pre.get("REGIMEN") or "")
        self.txtAgenciaAduanas.setText(pre.get("AGEN_ADUAN") or "")

        self.txtVolumen.setText(self._calcular_volumen_desde_preingreso(pre))

    def _calcular_volumen_desde_detalle(self) -> float:
        if not self.detalle:
            return 0.0

        total = 0.0
        for d in self.detalle:
            p_vol = d.get("p_vol")
            if p_vol is not None:
                try:
                    total += float(p_vol)
                except (TypeError, ValueError):
                    pass
        return round(total, 3)

    def _calcular_volumen_desde_preingreso(self, pre: dict) -> str:
        
        dim = (pre.get("DIMENSIONES") or "").lower().replace(" ", "")

        if "x" in dim:
            try:
                partes = dim.split("x")
                if len(partes) == 3:
                    l = float(partes[0])
                    a = float(partes[1])
                    h = float(partes[2])
                    vol_m3 = (l * a * h) / 1_000_000.0
                    return f"{vol_m3:.3f}"
            except ValueError:
                pass

        return ""

    def descargar_xml(self):

        h = dict(self.header) if self.header else {}

        if not h:
            QMessageBox.warning(self, "XML", "No hay datos consolidados (Warehouse Receipt) para generar el XML.")
            return

        def get_text(clave: str, default: str = "") -> str:
            valor = h.get(clave, default)
            if valor is None:
                return default
            return str(valor)

        now = datetime.now()

        base_name = f"RGME_4010_{get_text('n_dam')}_{self.cod_war or 'SINWR'}.xml"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar XML SEIDA 4010",
            base_name,
            "Archivos XML (*.xml)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".xml"):
            file_path += ".xml"

        root = ET.Element(
            "DeclarationMetaData",
            {
                "xsi:schemaLocation": "urn:wco:datamodel:PE:DocumentMetaData:1 DeclarationMetaData_PE_1p0.xsd",
                "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                "xmlns": "urn:wco:datamodel:PE:DocumentMetaData:1",
                "xmlns:ds": "urn:wco:datamodel:PE:MetaData_DS:1",
            },
        )

        ET.SubElement(root, "WCODataModelVersionCode").text = "3.7"
        ET.SubElement(root, "WCOTypeName").text = "DEC"
        ET.SubElement(root, "ResponsibleCountryCode").text = "PE"
        ET.SubElement(root, "ResponsibleAgencyName").text = "SUNAT"
        ET.SubElement(root, "FunctionalDefinition").text = "4010"

        decl = ET.SubElement(
            root,
            "Declaration",
            {
                "xmlns": "urn:wco:datamodel:PE:Declaration:1",
                "xmlns:ds": "urn:wco:datamodel:PE:Declaration_DS:1",
                "xmlns:eds": "urn:wco:datamodel:PE:Declaration_EDS:1",
            },
        )

        ET.SubElement(decl, "FunctionCode").text = "4010"
        ET.SubElement(decl, "FunctionalReferenceID").text = get_text("n_dam") or (self.cod_war or "")

        issue_dt = ET.SubElement(decl, "IssueDateTime")
        dt_str = ET.SubElement(issue_dt, "{urn:wco:datamodel:PE:Declaration_DS:1}DateTimeString")
        dt_str.set("formatCode", "202")
        dt_str.text = now.strftime("%Y-%m-%dT%H:%M:%S")

        ET.SubElement(decl, "VersionID").text = "1.0"

        submitter = ET.SubElement(decl, "Submitter")
        submitter_id = ET.SubElement(submitter, "ID")
        submitter_id.set("schemeID", "4")
        submitter_id.text = get_text("agente_aduana_cod", "00000000000")
        ET.SubElement(submitter, "RoleCode").text = "31"

        decl_office = ET.SubElement(decl, "DeclarationOffice")
        ET.SubElement(decl_office, "ID").text = get_text("zona_ae", "235")

        add_doc_dam = ET.SubElement(decl, "AdditionalDocument")
        ET.SubElement(add_doc_dam, "CategoryCode").text = get_text("regimen", "40")
        ET.SubElement(add_doc_dam, "ID").text = get_text("n_dam")[-6:]
        issue = ET.SubElement(add_doc_dam, "IssueDateTime")
        issue_dt2 = ET.SubElement(issue, "{urn:wco:datamodel:PE:Declaration_DS:1}DateTimeString")
        issue_dt2.set("formatCode", "602")
        issue_dt2.text = str(h.get("anio_dam") or now.year)
        ET.SubElement(add_doc_dam, "IssueLocationName").text = get_text("zona_ae", "235")
        ET.SubElement(add_doc_dam, "TypeCode").text = "830"

        add_doc2 = ET.SubElement(decl, "AdditionalDocument")
        ET.SubElement(add_doc2, "ID").text = f"WEB{now.strftime('%y%m%d%H%M%S')}"
        issue2 = ET.SubElement(add_doc2, "IssueDateTime")
        issue2_dt = ET.SubElement(issue2, "{urn:wco:datamodel:PE:Declaration_DS:1}DateTimeString")
        issue2_dt.set("formatCode", "602")
        issue2_dt.text = str(h.get("anio_dam") or now.year)
        ET.SubElement(add_doc2, "IssueLocationName").text = get_text("zona_ae", "235")
        ET.SubElement(add_doc2, "IssuingPartyID").text = submitter_id.text
        ET.SubElement(add_doc2, "TypeCode").text = "335"

        goods = ET.SubElement(decl, "GoodsShipment")

        add_doc_gs = ET.SubElement(goods, "AdditionalDocument")
        ET.SubElement(add_doc_gs, "CategoryCode").text = "GA"
        ET.SubElement(add_doc_gs, "TypeCode").text = "730"

        ai1 = ET.SubElement(goods, "AdditionalInformation")
        limit_dt = ET.SubElement(ai1, "LimitDateTime")
        limit_dt_str = ET.SubElement(limit_dt, "{urn:wco:datamodel:PE:Declaration_DS:1}DateTimeString")
        limit_dt_str.set("formatCode", "202")
        limit_dt_str.text = now.strftime("%Y-%m-%dT%H:%M:%S")
        ET.SubElement(ai1, "StatementTypeCode").text = "WHI"

        ai2 = ET.SubElement(goods, "AdditionalInformation")
        ET.SubElement(ai2, "Content").text = str(len(self.detalle or []))
        ET.SubElement(ai2, "StatementTypeCode").text = "AAQ"

        ai3 = ET.SubElement(goods, "AdditionalInformation")
        ET.SubElement(ai3, "Content").text = "MERCANCIA"
        ET.SubElement(ai3, "StatementTypeCode").text = "AFB"

        consignment = ET.SubElement(goods, "Consignment")
        final_place = ET.SubElement(consignment, "FinalTransportMeansLoadingPlace")
        ET.SubElement(final_place, "ID").text = "1"

        goods_meas = ET.SubElement(goods, "GoodsMeasure")
        ET.SubElement(goods_meas, "GrossMassMeasure").text = get_text("peso_wr", "0")

        gov_item = ET.SubElement(goods, "GovernmentAgencyGoodsItem")
        pack = ET.SubElement(gov_item, "Packaging")
        ET.SubElement(pack, "TypeCode").text = "B"

        wh_elem = ET.SubElement(goods, "Warehouse")
        ET.SubElement(wh_elem, "Name").text = get_text("n_dam") or (self.cod_war or "")
        wh_arrival = ET.SubElement(wh_elem, "ArrivalDateTime")
        wh_arrival_dt = ET.SubElement(wh_arrival, "{urn:wco:datamodel:PE:Declaration_DS:1}DateTimeString")
        wh_arrival_dt.set("formatCode", "202")
        wh_arrival_dt.text = now.strftime("%Y-%m-%dT%H:%M:%S")

        tree = ET.ElementTree(root)
        tree.write(file_path, encoding="utf-8", xml_declaration=True)

        QMessageBox.information(self, "XML", f"XML generado:\n{file_path}")

    def descargar_warehouse_pdf(self):

        h = self.header or {}
        detalle = self.detalle or []

        if not h:
            QMessageBox.warning(self, "PDF", "No hay datos consolidados (Warehouse Receipt) para generar el PDF.")
            return

        base_name = f"WR_{self.cod_war or 'SINWR'}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Warehouse Receipt",
            base_name,
            "Archivos PDF (*.pdf)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".pdf"):
            file_path += ".pdf"

        c = canvas.Canvas(file_path, pagesize=A4)
        width, height = A4

        x0 = 40
        y = height - 40

        c.setFont("Helvetica-Bold", 12)
        c.drawString(x0, y, "TALMA SERVICIOS AEROPORTUARIOS S.A.")
        y -= 18
        c.drawString(x0, y, "WAREHOUSE RECEIPT : INFORMACION GENERAL")
        y -= 24

        c.setFont("Helvetica", 9)
        c.drawString(x0, y, f"Aerolínea: {h.get('aerolinea', '')}")
        y -= 12
        c.drawString(x0, y, f"Nro. Warehouse: {self.cod_war or ''}")
        y -= 12
        c.drawString(x0, y, f"Guía Madre: {h.get('mawb','') or self.txtGuiaMadre.text()}")
        y -= 12
        c.drawString(x0, y, f"Guía Hija: {h.get('hawb','') or self.txtGuiaHija.text()}")
        y -= 12
        c.drawString(x0, y, f"Exportador: {h.get('exportador_nom','') or self.txtExportador.text()}")
        y -= 12
        c.drawString(x0, y, f"Consignatario: {h.get('consignatario_nom','')}")
        y -= 12
        c.drawString(x0, y, f"Agente de Carga: {h.get('agente_carga_nom','') or self.txtAgenteCarga.text()}")
        y -= 12
        c.drawString(x0, y, f"Agencia de Aduanas: {h.get('agente_aduana_nom','') or self.txtAgenciaAduanas.text()}")
        y -= 12
        c.drawString(x0, y, f"Nro. DAM: {h.get('n_dam','') or self.txtNumeroDam.text()}")
        y -= 12
        c.drawString(x0, y, f"Canal: {h.get('canal_nombre','')}")
        y -= 18

        c.setFont("Helvetica-Bold", 9)
        c.drawString(x0, y, "Totales")
        y -= 12
        c.setFont("Helvetica", 9)
        c.drawString(x0, y, f"Bultos/Rec: {h.get('bul_wr') or self.txtBultos.text() or 0}")
        y -= 12
        c.drawString(x0, y, f"Kilos/Rec: {h.get('peso_wr') or self.txtKilo.text() or 0}")
        y -= 12
        c.drawString(x0, y, f"P/Volumen: {h.get('vol_wr') or self.txtVolumen.text() or 0}")
        y -= 18

        c.setFont("Helvetica-Bold", 8)
        c.drawString(x0,      y, "Item")
        c.drawString(x0 + 40, y, "Bultos/Rec")
        c.drawString(x0 + 110,y, "Largo")
        c.drawString(x0 + 160,y, "Ancho")
        c.drawString(x0 + 210,y, "Alto")
        c.drawString(x0 + 260,y, "P/Volumen")
        y -= 10
        c.line(x0, y, width - x0, y)
        y -= 8

        c.setFont("Helvetica", 8)
        for d in detalle:
            if y < 80:
                c.showPage()
                y = height - 60
                c.setFont("Helvetica-Bold", 8)
                c.drawString(x0,      y, "Item")
                c.drawString(x0 + 40, y, "Bultos/Rec")
                c.drawString(x0 + 110,y, "Largo")
                c.drawString(x0 + 160,y, "Ancho")
                c.drawString(x0 + 210,y, "Alto")
                c.drawString(x0 + 260,y, "P/Volumen")
                y -= 10
                c.line(x0, y, width - x0, y)
                y -= 8
                c.setFont("Helvetica", 8)

            c.drawString(x0,      y, str(d.get("item")))
            c.drawString(x0 + 40, y, str(d.get("bultos")))
            c.drawString(x0 + 110, y, f"{d.get('largo'):.2f}")
            c.drawString(x0 + 160, y, f"{d.get('ancho'):.2f}")
            c.drawString(x0 + 210, y, f"{d.get('alto'):.2f}")
            c.drawString(x0 + 260, y, f"{d.get('p_vol'):.2f}")
            y -= 12

        y = 60
        c.setFont("Helvetica", 7)
        c.drawString(x0, y, "La emisión del presente documento se realiza como parte del proceso de transporte aéreo.")
        y -= 10
        c.drawString(x0, y, "La responsabilidad de la empresa se rige por las normas de indemnización del transporte aéreo.")
        y -= 10
        c.drawString(x0, y, "Salvo convenio especial y expreso suscrito por TALMA.")
        c.showPage()
        c.save()

        QMessageBox.information(self, "PDF", f"Warehouse Receipt generado:\n{file_path}")

    def transmitir(self):
        
        QMessageBox.information(
            self,
            "Transmisión",
            "Transmisión exitosa"
        )

    def cerrar_sesion(self):

        reply = QMessageBox.question(
            self,
            "Cerrar Sesión",
            "¿Está seguro de que desea cerrar la sesión?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.reject()
            QApplication.quit()
            import os
            os.execv(sys.executable, [sys.executable] + sys.argv)

#  5. VENTANA PRINCIPAL
class MainWindow(QMainWindow):

    def __init__(self, usuario_id=None):
        super().__init__()
        self.usuario_id = usuario_id

        self.tabs = QTabWidget()

        self.tab_pre_ingreso = PreIngresoWindow(usuario_id=usuario_id)
        self.tab_ingreso_alm = IngresoAlmacenWindow(usuario_id=usuario_id)
        self.tab_recepcion   = RecepcionDialog(usuario_id=usuario_id)

        self.tabs.addTab(self.tab_pre_ingreso, "Pre-Ingreso")
        self.tabs.addTab(self.tab_ingreso_alm, "Ingreso Almacén")
        self.tabs.addTab(self.tab_recepcion,   "Recepción")

        self.setCentralWidget(self.tabs)

        self.setWindowTitle("Gestión de Guías Aéreas - TalmaWR")

    def cerrar_sesion(self):
        reply = QMessageBox.question(
            self,
            "Cerrar Sesión",
            "¿Está seguro de que desea cerrar la sesión?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            import os
            os.execv(sys.executable, [sys.executable] + sys.argv)


#  6. DIALOGO DE LOGIN
class LoginDialog(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(UI_LOGIN, self)
        self.setWindowTitle("Login")
        self.txtContrasena.setEchoMode(QLineEdit.Password)
        self.btnIngresar.clicked.connect(self.intentar_login)
        self.usuario_id = None
        self.usuario = None
        self.rol = None

    def intentar_login(self):
        usuario = self.txtUsuario.text().strip()
        contrasena = self.txtContrasena.text().strip()
        if not usuario or not contrasena:
            QMessageBox.warning(self, "Login", "Ingrese usuario y contraseña.")
            return
        cur = db.conn.cursor()
        cur.execute("SELECT id, usuario, contrasena FROM Usuarios WHERE usuario = ?", (usuario,))
        row = cur.fetchone()
        if not row:
            QMessageBox.warning(self, "Login", "Usuario no encontrado.")
            return
        usuario_id, db_usuario, db_contrasena = row
        if contrasena != db_contrasena:
            QMessageBox.warning(self, "Login", "Contraseña incorrecta.")
            return
        self.usuario_id = usuario_id
        self.usuario = usuario
        if usuario == "AGCARGA":
            self.rol = "preingreso"
        elif usuario == "ALMACEN":
            self.rol = "ingreso"
        elif usuario == "TRANSMISIONES":
            self.rol = "recepcion"
        elif usuario == "ADMIN":
            self.rol = "admin"
        else:
            self.rol = None
        self.close()

    def clear_fields(self):
        self.txtUsuario.clear()
        self.txtContrasena.clear()
        self.usuario_id = None
        self.usuario = None
        self.rol = None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    login = LoginDialog()
    login.show()
    app.exec_()
    
    usuario_id = login.usuario_id
    usuario = login.usuario
    rol = login.rol
    
    if usuario_id and rol:
        win = None
        if rol == "preingreso":
            win = PreIngresoWindow(usuario_id=usuario_id)
        elif rol == "ingreso":
            win = IngresoAlmacenWindow(usuario_id=usuario_id)
        elif rol == "recepcion":
            win = RecepcionDialog(usuario_id=usuario_id)
        elif rol == "admin":
            win = MainWindow(usuario_id=usuario_id)
        else:
            QMessageBox.critical(None, "Login", "Rol no reconocido.")
            sys.exit(1)
        
        if win:
            if isinstance(win, QDialog):
                win.exec_()
            else:
                win.show()
                sys.exit(app.exec_())
    else:
        sys.exit(0)