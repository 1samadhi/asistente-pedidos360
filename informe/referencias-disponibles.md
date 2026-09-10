# Referencias disponibles para citar

Buscar referencias es de lo que la pauta **sí** autoriza apoyar con IA
(*«utilizar la IA como apoyo para mejorar redacción, buscar referencias o crear
diagramas»*, página 4). Esta lista existe para eso: para que al redactar los apartados E
y F tengan a mano fuentes reales, ya formateadas en APA, y no tengan que buscarlas desde
cero.

**Citen solo las que efectivamente usen.** Una referencia en la lista que no aparece en el
texto es un error de forma en APA.

---

## Verificadas contra la fuente

Estas cuatro se comprobaron consultando la publicación, no se citan de memoria.

**Fundamento de RAG** — respalda la pregunta 1 del apartado E (¿por qué RAG y no un LLM
respondiendo de memoria?).

> Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H.,
> Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., & Kiela, D. (2020).
> Retrieval-augmented generation for knowledge-intensive NLP tasks. *Advances in Neural
> Information Processing Systems, 33*. https://arxiv.org/abs/2005.11401

**Fusión de rankings (RRF)** — respalda la decisión de fusionar la búsqueda densa con la
léxica, y el porqué de la constante *k* = 60 usada en `recuperador.py`.

> Cormack, G. V., Clarke, C. L. A., & Büttcher, S. (2009). Reciprocal rank fusion
> outperforms Condorcet and individual rank learning methods. *Proceedings of the 32nd
> International ACM SIGIR Conference on Research and Development in Information
> Retrieval*, 758–759. https://doi.org/10.1145/1571941.1572114

**Embeddings de oraciones** — respalda la elección del modelo local de embeddings y la
pregunta 4 del apartado E.

> Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using Siamese
> BERT-networks. *Proceedings of the 2019 Conference on Empirical Methods in Natural
> Language Processing*. https://arxiv.org/abs/1908.10084

**Versión multilingüe del anterior** — es la técnica detrás del modelo
`paraphrase-multilingual-MiniLM-L12-v2` que usa el proyecto.

> Reimers, N., & Gurevych, I. (2020). Making monolingual sentence embeddings multilingual
> using knowledge distillation. *Proceedings of the 2020 Conference on Empirical Methods
> in Natural Language Processing*.

## Ya citadas en el informe

> Internet Engineering Task Force. (2012). *RFC 6749: The OAuth 2.0 authorization
> framework*. https://www.rfc-editor.org/rfc/rfc6749.txt
>
> Internet Engineering Task Force. (2015). *RFC 7519: JSON Web Token (JWT)*.
> https://www.rfc-editor.org/rfc/rfc7519.txt
>
> Ley N° 19.628. *Sobre protección de la vida privada*. Diario Oficial de la República de
> Chile, 28 de agosto de 1999.
>
> OWASP Foundation. (2023). *API Security Top 10*.
> https://owasp.org/API-Security/editions/2023/en/0x11-t10/

## Software utilizado

En APA, el software se cita por su documentación cuando no hay una publicación asociada
clara. Completen la fecha de consulta el día que entreguen.

> LangChain. (2026). *LangChain documentation*. https://python.langchain.com/docs/
>
> Meta AI. (2026). *Faiss: A library for efficient similarity search* [software].
> https://faiss.ai/

> **Aviso sobre FAISS.** Existe además el artículo de Johnson, Douze y Jégou sobre
> búsqueda de similitud a escala de mil millones, publicado en *IEEE Transactions on Big
> Data*. **No conseguí verificar el año exacto** —las fuentes consultadas se
> contradicen entre 2019 y 2021— así que no lo incluyo con datos que no pude comprobar.
> Si quieren citar el artículo en vez de la biblioteca, verifiquen ustedes la ficha en
> IEEE Xplore antes de ponerlo.

---

## Qué respalda cada pregunta del apartado E

| Pregunta de E | Referencia útil |
|---|---|
| 1. ¿Por qué RAG y no memoria del modelo? | Lewis et al. (2020) |
| 2. ¿Por qué un agente con herramientas? | Ninguna: el argumento sale de los datos del propio proyecto |
| 3. ¿Por qué fuentes internas y externas? | RFC 6749 y 7519, OWASP |
| 4. ¿Por qué embeddings locales? | Reimers y Gurevych (2019, 2020) |
| 5. ¿Por qué el ranking se calcula en la herramienta? | Ninguna: la evidencia está en el informe |
| 6. ¿Y si la precisión no estuviera acotada? | Cormack et al. (2009) |

Fíjense en las dos filas sin referencia: son argumentos que **solo pueden salir de este
proyecto**, y probablemente sean los que más valore quien evalúe.
