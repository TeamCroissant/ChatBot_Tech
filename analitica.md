# Análisis de Interacciones de Usuarios

## Almacenamiento inicial en DynamoDB
Las conversaciones y usuarios se almacenan en dos tablas de DynamoDB:
- `talento-tech-hackaton-conversations`
- `talento-tech-hackaton-users`

##  Pipeline de transformación (ETL)
Para hacer que los datos sean analizables en SQL:
- Un **Glue Crawler** escanea ambas tablas de DynamoDB.
- Este crawler genera un esquema estructurado en el **Glue Data Catalog**, interpretando los datos semi-estructurados.

##  Consulta SQL con Athena
- Con el esquema en el catálogo, **Amazon Athena** puede consultar los datos directamente usando SQL.
- Esto permite ejecutar queries complejas sobre las conversaciones, usuarios, y sus sentimientos.

##  Visualización con Amazon QuickSight
- **QuickSight** consume los resultados de Athena para generar dashboards visuales.
- Estos dashboards permiten entender patrones de uso, emociones predominantes, y comportamiento de los usuarios.

---

Este pipeline transforma las interacciones de Telegram guardadas en DynamoDB en datos analizables, todo sin mover la información a una base relacional tradicional.
