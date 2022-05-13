<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="2.0"
xmlns:d="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/facturaElectronica"
exclude-result-prefixes="d">
  <xsl:template match="/">
    <html>
      <body>
        <table style="  border-collapse: collapse; width: 100%;">
          <tr>
            <td colspan="14" style="background-color: #3b9390;"><center><h1 style=" color: white;"><xsl:value-of select="d:FacturaElectronica/d:Emisor/d:Nombre" /></h1></center></td>
          </tr>
          <tr>
            <td colspan="7"><h5 style="font-weight: bold;">Datos Proveedor</h5></td>
            <td colspan="7"><h5 style="font-weight: bold;">Datos Receptor</h5></td>
          </tr>
          <tr>
            <td colspan="7"><span style='font-weight: bold;'>Tipo Identificacion: </span><xsl:value-of select="d:FacturaElectronica/d:Emisor/d:Identificacion/d:Tipo"/></td>
            <td colspan="7"><span style='font-weight: bold;'>Tipo Identificacion: </span> <xsl:value-of select="d:FacturaElectronica/d:Receptor/d:Identificacion/d:Tipo" /></td>
          </tr>
          <tr>
            <td colspan="7"><span style='font-weight: bold;'>Numero Identificacion: </span><xsl:value-of select="d:FacturaElectronica/d:Emisor/d:Identificacion/d:Numero"/></td>
            <td colspan="7"><span style='font-weight: bold;'>Numero Identificacion: </span><xsl:value-of select="d:FacturaElectronica/d:Receptor/d:Identificacion/d:Numero"/></td>
          </tr>
          <tr>
            <td colspan="7"><span style='font-weight: bold;'>Telefono: </span><xsl:value-of select="d:FacturaElectronica/d:Emisor/d:Telefono/d:NumTelefono" /></td>
            <td colspan="7"><span style='font-weight: bold;'>Telefono: </span><xsl:value-of select="d:FacturaElectronica/d:Receptor/d:Telefono/d:NumTelefono" /></td>
          </tr>
          <tr>
            <td colspan="7" style="padding-bottom: 6px;"><span style='font-weight: bold;'>Email: </span><xsl:value-of select="d:FacturaElectronica/d:Emisor/d:CorreoElectronico"/></td>
            <td colspan="7" style="padding-bottom: 6px;"><span style='font-weight: bold;'>Email: </span><xsl:value-of select="d:FacturaElectronica/d:Receptor/d:CorreoElectronico"/></td>
          </tr>
          <tr>
            <td colspan="7" style="padding-bottom: 6px;"><span style='font-weight: bold;'>Tipo de cambio: </span><xsl:value-of select="d:FacturaElectronica/d:ResumenFactura/d:CodigoTipoMoneda/d:TipoCambio"/></td>
          </tr>
          <tr>
            <th colspan="2" style="background-color: #dcdfe5;padding-top: 6px;
            padding-bottom: 6px;">No</th>
            <th colspan="2" style="background-color: #dcdfe5;padding-top: 6px;
            padding-bottom: 6px;">Cant</th>
            <th colspan="2" style="background-color: #dcdfe5;padding-top: 6px;
            padding-bottom: 6px;">Unid /Cod / Producto</th>
            <th colspan="2" style="background-color: #dcdfe5;padding-top: 6px;
            padding-bottom: 6px;">Precio</th>
            <th colspan="2" style="background-color: #dcdfe5;padding-top: 6px;
            padding-bottom: 6px;">Descuento</th>
            <th colspan="2" style="background-color: #dcdfe5;padding-top: 6px;
            padding-bottom: 6px;">impuesto</th>
            <th colspan="2" style="background-color: #dcdfe5;padding-top: 6px;
            padding-bottom: 6px;">Total de linea</th>
          </tr>
          <xsl:for-each select="d:FacturaElectronica/d:DetalleServicio/d:LineaDetalle">
            <tr>
              <td colspan="2" style="padding-top: 3px; border-bottom: 1px solid #ddd;"><xsl:value-of select="d:NumeroLinea" /></td>
              <td colspan="2" style="padding-top: 3px; border-bottom: 1px solid #ddd;"><xsl:value-of select="d:Cantidad" /></td>
              <td colspan="2" style="padding-top: 3px; border-bottom: 1px solid #ddd;"><xsl:value-of select="d:UnidadMedida"/> / <xsl:value-of select="d:Codigo/d:Codigo"/> / <xsl:value-of select="d:Detalle"/></td>
              <td colspan="2" style="padding-top: 3px; border-bottom: 1px solid #ddd;"><xsl:value-of select="d:PrecioUnitario"/></td>
              <td colspan="2" style="padding-top: 3px; border-bottom: 1px solid #ddd;"><xsl:value-of select="d:Descuento"/></td>
              <td colspan="2" style="padding-top: 3px; border-bottom: 1px solid #ddd;"><xsl:value-of select="d:Impuesto/d:Tarifa"/> %</td>
              <td colspan="2" style="padding-top: 3px; border-bottom: 1px solid #ddd;"><xsl:value-of select="d:MontoTotalLinea"/></td>
            </tr>
          </xsl:for-each>
          <tr>
            <th colspan="2" style="background-color: #dcdfe5;padding-top: 6px;
            padding-bottom: 6px;margin-top: 10px;">Otros Cargos</th>
            <th colspan="2" style="background-color: #dcdfe5;padding-top: 6px;
            padding-bottom: 6px; margin-top: 10px;">Monto</th>
          </tr>
           <xsl:for-each select="d:FacturaElectronica/d:OtrosCargos">
            <tr>
              <td colspan="2" style="padding-top: 3px;"><xsl:value-of select="d:Detalle" /></td>
              <td colspan="2" style="padding-top: 3px;"><xsl:value-of select="d:MontoCargo" /></td>
            </tr>
          </xsl:for-each>

         <tr>
            <td colspan='12'></td>
            <td><span style='font-weight: bold;'>
            Sub Total: </span><xsl:value-of
           select="d:FacturaElectronica/d:ResumenFactura/d:TotalVenta"/>
           </td>
         </tr>
         <tr>
            <td colspan='12'></td>
            <td><span style='font-weight: bold;'>
            Descuento: </span><xsl:value-of
           select="d:FacturaElectronica/d:ResumenFactura/d:TotalDescuentos"/>
           </td>
         </tr>
         <tr>
            <td colspan='12'></td>
            <td><span style='font-weight: bold;'>
            Imp Venta: </span><xsl:value-of
            select="d:FacturaElectronica/d:ResumenFactura/d:TotalImpuesto"/>
            </td>
         </tr>
         <tr>
            <td colspan='12'></td>
            <td><span style='font-weight: bold;'>
            Total: </span><xsl:value-of
            select="d:FacturaElectronica/d:ResumenFactura/d:TotalComprobante"/>
           </td>
         </tr>
        </table>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
