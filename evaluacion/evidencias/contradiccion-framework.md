# Evidencia · comportamiento ante un corpus contradictorio

**Fecha:** 2026-09-09  
**Modelo:** openai/gpt-oss-120b · recuperacion hibrida 0.8/0.2, k=5, tope 2 por archivo

## La contradiccion

El corpus interno se contradice sobre un hecho verificable. `00-readme-pedidos360.md`
afirma dos veces que el frontend es **"SPA React + Vite"** (lineas 68 y 86), mientras
`06-frontend-angular.md`, `08-readme-frontend.md` y el propio nombre del directorio
`front-angular/` dicen **Angular**. La contradiccion es real y estaba en la
documentacion antes de este proyecto; no se introdujo para la prueba.

Interesa porque un asistente que cita fuentes puede citar la equivocada con total
seguridad. Es el escenario que el indicador IE4 pide examinar.

## Fragmentos recuperados

1. `08-readme-frontend.md` — Pedidos360 — Frontend
2. `08-readme-frontend.md` — Pedidos360 — Frontend > Construccion
3. `06-frontend-angular.md` — Frontend Angular con MSAL > Paginas
4. `06-frontend-angular.md` — Frontend Angular con MSAL
5. `00-readme-pedidos360.md` — EXP1 — Arquitectura segura en la nube con OIDC y OAuth 2.0 > Emisores 

## Respuesta del asistente

```
El frontend de Pedidos360 está construido con **Angular**【2】.
```

## Observación

Hechos, sin interpretar:

1. La respuesta es **correcta**: el frontend es Angular.
2. El fragmento que afirma lo contrario **sí estaba en el contexto**, en la posición 5.
3. El asistente **no mencionó** que una de sus fuentes lo contradice: resolvió el
   conflicto en silencio.
4. Cuatro de los cinco fragmentos venían de los dos documentos que dicen Angular. El
   tope de dos fragmentos por archivo evitó que un solo documento copara el resultado.

El punto 3 es el que queda abierto: el sistema acertó, pero no por haber detectado el
desacuerdo. Con la distribución invertida —más fragmentos del documento equivocado— no
hay nada en el diseño actual que garantice el mismo resultado.
