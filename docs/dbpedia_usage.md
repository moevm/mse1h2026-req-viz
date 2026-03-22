# Использование DBPedia для наполнения базы данных

## 1. Возможности извлечения данных из DBPedia

DBPedia предоставляет несколько способов доступа к данным, каждый из которых подходит для разных сценариев использования:

### SPARQL Endpoint
Основной способ взаимодействия с DBPedia - через SPARQL endpoint, который позволяет выполнять сложные запросы к базе знаний.

**URL**: `https://dbpedia.org/sparql`

SPARQL endpoint работает на базе OpenLink Virtuoso

**Пример использования**:
```bash
curl -H "Accept: application/json" "https://dbpedia.org/sparql?query=select+distinct+%3FConcept+where+%7B%5B%5D+a+%3FConcept%7D+LIMIT+100"
```

### Linked Data Interface (https)
Позволяет получать информацию о конкретных сущностях через https-запросы.

**Формат URL**: `https://dbpedia.org/resource/{Entity_Name}`

**Механизм работы**:
1. Всегда возвращают http 303 See Other (например, `https://dbpedia.org/resource/Berlin`)
2. В заголовке Location указывается URI в формате `https://dbpedia.org/data/{Entity_Name}.{extension}`

**Поддерживаемые форматы**:
- RDF/XML (`application/rdf+xml`)
- Turtle (`text/turtle`)
- JSON-LD (`application/ld+json`)
- N-Triples (`application/n-triples`)
- TriG (`application/trig`)
- Atom (`application/atom+xml`)
- JSON (`application/json`)

**Пример использования**:
```bash
curl -L -H "Accept: application/rdf+xml" https://dbpedia.org/resource/Apache_Kafka
```

**Дополнительные параметры**:
- `https://dbpedia.org/page/{Entity_Name}`: HTML страница с описанием сущности
- `https://dbpedia.org/data/{Entity_Name}.rdf`: Прямой доступ к RDF/XML представлению

### REST API (экспериментальный)
Новый интерфейс на основе Spring и Swagger, предоставляющий более удобный способ доступа к данным.

**Особенности**:
- Более простой в использовании по сравнению с SPARQL
- Доступ через DBpedia Ontology
- Поддержка Swagger UI для тестирования и документации
- RESTful архитектура с предсказуемыми URL путями

**Доступные endpoints**:
- `/api/entity/{entityId}`: Получение информации о сущности
- `/api/search`: Поиск сущностей по ключевым словам
- `/api/category/{categoryId}`: Получение сущностей из категории

## 2. Отличия DBPedia от Wikidata

| Характеристика | DBPedia | Wikidata |
|----------------|---------|----------|
| **Источник данных** | Автоматически извлекается из Wikipedia | Создается и поддерживается сообществом |
| **Структура** | Структурированная, основанная на шаблонах Wikipedia | Гибкая, пользовательская структура с произвольными свойствами |
| **Онтология** | DBpedia Ontology с предопределенными классами и свойствами | Гибкие свойства у каждой модели |
| **Покрытие** | Основано на статьях Wikipedia всех языковых версий | Более широкое, включая внешние источники |
| **Качество данных** | Зависит от качества статей Wikipedia | Проверяется сообществом |
| **Язык запросов** | SPARQL | SPARQL |
| **Идентификаторы** | URI на основе названий статей Wikipedia (https://dbpedia.org/resource/...) | Q-идентификаторы (Q1, Q2, ...) с мультиязычными метками |
| **Связи** | Автоматически извлеченные связи из текста и структуры Wikipedia | Ручное создание связей сообществом |

## 3. Основные пространства имен и префиксы

### DBR (DBpedia Resource)
URI для конкретных сущностей. Формируется на основе названия статьи в Wikipedia с заменой пробелов на подчеркивания.

**Примеры**:
- `https://dbpedia.org/resource/Apache_Kafka`
- `https://dbpedia.org/resource/Google`
- `https://dbpedia.org/resource/Python_(programming_language)`
- `https://dbpedia.org/resource/New_York_City`
- `https://dbpedia.org/resource/Barack_Obama`

### DBO (DBpedia Ontology)
Онтология DBpedia с предопределенными классами и свойствами для структурирования данных.

**Основные классы**:
- `dbo:Software` - программное обеспечение
- `dbo:Company` - компания
- `dbo:Person` - персоналия
- `dbo:ProgrammingLanguage` - язык программирования
- и т.д.

**Основные свойства**:
- `dbo:abstract` - описание/аннотация статьи
- `dbo:developer` - разработчик (организация или персона)
- `dbo:product` - продукт компании
- `dbo:license` - лицензия
- и т.д.

### RDF Schema
`https://www.w3.org/2000/01/rdf-schema#`

**Основные свойства**:
- `rdfs:label` - название сущности (может быть на разных языках)
- `rdfs:comment` - комментарий или описание
- `rdfs:subClassOf` - отношение подкласса (наследование)
- и т.д.

### Dublin Core
`https://www.dublincore.org/specifications/dublin-core/dcmi-terms/`

**Основные свойства**:
- `dct:title` - заголовок
- `dct:creator` - создатель
- `dct:subject` - тема/категория
- `dct:description` - описание
- и т.д.

### FOAF (Friend of a Friend)
`https://xmlns.com/foaf/spec/`

## 4. Пример получения данных

Для получения информации о технологии Apache Kafka, можно использовать следующий SPARQL-запрос:

```sparql
SELECT ?label ?abstract ?developer ?license ?homepage ?type ?releaseDate ?latestReleaseVersion ?programmingLanguage ?category ?influenced ?influencedBy ?relatedTechnologies
WHERE {
  dbr:Apache_Kafka rdfs:label ?label .
  OPTIONAL { dbr:Apache_Kafka dbo:abstract ?abstract . }
  OPTIONAL { dbr:Apache_Kafka dbo:developer ?developer . }
  OPTIONAL { dbr:Apache_Kafka dbo:license ?license . }
  OPTIONAL { dbr:Apache_Kafka dbo:homepage ?homepage . }
  OPTIONAL { dbr:Apache_Kafka a ?type . }
  OPTIONAL { dbr:Apache_Kafka dbo:releaseDate ?releaseDate . }
  OPTIONAL { dbr:Apache_Kafka dbo:latestReleaseVersion ?latestReleaseVersion . }
  OPTIONAL { dbr:Apache_Kafka dbo:programmingLanguage ?programmingLanguage . }
  OPTIONAL { dbr:Apache_Kafka dct:subject ?category . }

  OPTIONAL { ?influenced dbo:influencedBy dbr:Apache_Kafka . }
  OPTIONAL { dbr:Apache_Kafka dbo:influencedBy ?influencedBy . }
  OPTIONAL { ?relatedTechnologies dbo:wikiPageWikiLink dbr:Apache_Kafka .
             FILTER (?relatedTechnologies != dbr:Apache_Kafka) }

  FILTER (lang(?label) = 'en')
}
LIMIT 3
```

**Пример ответа:**
```json
{
  "head": {
    "link": [],
    "vars": [
      "label",
      "abstract",
      "developer",
      "license",
      "homepage",
      "type",
      "releaseDate",
      "latestReleaseVersion",
      "programmingLanguage",
      "category",
      "influenced",
      "influencedBy",
      "relatedTechnologies"
    ]
  },
  "results": {
    "distinct": false,
    "ordered": true,
    "bindings": [
      {
        "label": {
          "type": "literal",
          "xml:lang": "en",
          "value": "Apache Kafka"
        },
        "developer": {
          "type": "uri",
          "value": "http://dbpedia.org/resource/The_Apache_Software_Foundation"
        },
        "license": {
          "type": "uri",
          "value": "http://dbpedia.org/resource/Apache_License"
        },
        "type": {
          "type": "uri",
          "value": "http://www.w3.org/2002/07/owl#Thing"
        },
        "programmingLanguage": {
          "type": "uri",
          "value": "http://dbpedia.org/resource/Scala_(programming_language)"
        },
        "category": {
          "type": "uri",
          "value": "http://dbpedia.org/resource/Category:Free_software_programmed_in_Java_(programming_language)"
        },
        "relatedTechnologies": {
          "type": "uri",
          "value": "http://dbpedia.org/resource/IBM_System_Management_Facilities"
        }
      },
      {
        "label": {
          "type": "literal",
          "xml:lang": "en",
          "value": "Apache Kafka"
        },
        "developer": {
          "type": "uri",
          "value": "http://dbpedia.org/resource/The_Apache_Software_Foundation"
        },
        "license": {
          "type": "uri",
          "value": "http://dbpedia.org/resource/Apache_License"
        },
        "type": {
          "type": "uri",
          "value": "http://www.w3.org/2002/07/owl#Thing"
        },
        "programmingLanguage": {
          "type": "uri",
          "value": "http://dbpedia.org/resource/Scala_(programming_language)"
        },
        "category": {
          "type": "uri",
          "value": "http://dbpedia.org/resource/Category:Free_software_programmed_in_Java_(programming_language)"
        },
        "relatedTechnologies": {
          "type": "uri",
          "value": "http://dbpedia.org/resource/List_of_Apache_Software_Foundation_projects"
        }
      },
      {
        "label": {
          "type": "literal",
          "xml:lang": "en",
          "value": "Apache Kafka"
        },
        "developer": {
          "type": "uri",
          "value": "http://dbpedia.org/resource/The_Apache_Software_Foundation"
        },
        "license": {
          "type": "uri",
          "value": "http://dbpedia.org/resource/Apache_License"
        },
        "type": {
          "type": "uri",
          "value": "http://www.w3.org/2002/07/owl#Thing"
        },
        "programmingLanguage": {
          "type": "uri",
          "value": "http://dbpedia.org/resource/Scala_(programming_language)"
        },
        "category": {
          "type": "uri",
          "value": "http://dbpedia.org/resource/Category:Free_software_programmed_in_Java_(programming_language)"
        },
        "relatedTechnologies": {
          "type": "uri",
          "value": "http://dbpedia.org/resource/Message_broker"
        }
      }
    ]
  }
}
```