# Flowchart

Use for process flows, decision trees, algorithms, and system architectures.

## Basic Example

```mermaid
flowchart TD
    A[Start] --> B{Decision?}
    B -->|Yes| C[Action 1]
    B -->|No| D[Action 2]
    C --> E[End]
    D --> E
```

## Direction

| Keyword | Direction |
|---------|-----------|
| `TD` / `TB` | Top → Down |
| `LR` | Left → Right |
| `BT` | Bottom → Top |
| `RL` | Right → Left |

- Use `LR` for wide processes (pipelines, data flows)
- Use `TD` for deep hierarchies (org charts, call stacks)

## Node Shapes

| Syntax | Shape | Use For |
|--------|-------|---------|
| `[text]` | Rectangle | Actions, steps |
| `(text)` | Rounded rectangle | Start/End |
| `{text}` | Diamond | Decisions |
| `([text])` | Stadium | Events, triggers |
| `[[text]]` | Subroutine | Sub-processes |
| `[(text)]` | Cylinder | Databases, storage |
| `((text))` | Circle | Connectors |
| `>text]` | Asymmetric | Inputs |
| `{{text}}` | Hexagon | Preparation steps |
| `[/text/]` | Parallelogram | I/O |
| `[\text\]` | Trapezoid alt | Manual operations |

## Link Types

| Syntax | Meaning |
|--------|---------|
| `-->` | Arrow (directional) |
| `---` | Line (undirectional) |
| `-.->` | Dotted arrow |
| `==>` | Thick arrow |
| `-->│label│` | Arrow with label |
| `-- label -->` | Arrow with label (alt) |
| `~~~` | Invisible link (for layout) |

## Subgraphs

Group related nodes:

```mermaid
flowchart LR
    subgraph Frontend
        A[React App] --> B[API Client]
    end
    subgraph Backend
        C[API Server] --> D[Database]
    end
    B --> C
```

Subgraphs can be nested and linked:

```mermaid
flowchart TD
    subgraph Cloud
        subgraph VPC
            LB[Load Balancer] --> SVC[Service]
        end
    end
    User --> LB
```

## Styling

### classDef

```mermaid
flowchart LR
    A[Service A]:::primary --> B[Service B]:::secondary
    B --> C[(Database)]:::storage

    classDef primary fill:#F5F2EF,stroke:#6B5E57,color:#3F3631
    classDef secondary fill:#EAE2DB,stroke:#8A7668,color:#3F3631
    classDef storage fill:#F8F6F3,stroke:#DDD6CF,color:#24201D
```

### Inline style

```mermaid
flowchart LR
    A --> B
    style A fill:#F5F2EF,stroke:#6B5E57,color:#3F3631,stroke-width:2px
```

### Link style

```mermaid
flowchart LR
    A --> B --> C
    linkStyle 0 stroke:#6B5E57,stroke-width:2px
    linkStyle 1 stroke:blue
```

## Advanced Patterns

### Architecture Diagram

```mermaid
flowchart TD
    subgraph Client Layer
        Web[Web App]
        Mobile[Mobile App]
    end

    subgraph API Layer
        GW[API Gateway]
        Auth[Auth Service]
    end

    subgraph Service Layer
        UserSvc[User Service]
        OrderSvc[Order Service]
        PaySvc[Payment Service]
    end

    subgraph Data Layer
        PG[(PostgreSQL)]
        Redis[(Redis)]
        MQ[Message Queue]
    end

    Web & Mobile --> GW
    GW --> Auth
    GW --> UserSvc & OrderSvc & PaySvc
    UserSvc --> PG
    OrderSvc --> PG & MQ
    PaySvc --> Redis & MQ

    classDef client fill:#F5F2EF,stroke:#6B5E57,color:#3F3631
    classDef api fill:#EAE2DB,stroke:#8A7668,color:#3F3631
    classDef service fill:#FFFFFF,stroke:#DDD6CF,color:#24201D
    classDef data fill:#F1EDE8,stroke:#6F6660,color:#24201D

    class Web,Mobile client
    class GW,Auth api
    class UserSvc,OrderSvc,PaySvc service
    class PG,Redis,MQ data
```

### Decision Tree

```mermaid
flowchart TD
    Start{Is it urgent?}
    Start -->|Yes| Important{Is it important?}
    Start -->|No| NotUrgent{Is it important?}
    Important -->|Yes| DO[Do it NOW]
    Important -->|No| DELEGATE[Delegate it]
    NotUrgent -->|Yes| SCHEDULE[Schedule it]
    NotUrgent -->|No| ELIMINATE[Eliminate it]

    classDef do fill:#FFFFFF,stroke:#52C41A,color:#24201D
    classDef delegate fill:#F5F2EF,stroke:#6B5E57,color:#3F3631
    classDef schedule fill:#FFFFFF,stroke:#FAAD14,color:#24201D
    classDef eliminate fill:#FFFFFF,stroke:#FF4D4F,color:#24201D

    class DO do
    class DELEGATE delegate
    class SCHEDULE schedule
    class ELIMINATE eliminate
```

## Best Practices

1. **Keep nodes concise** — 3-5 words max per node label
2. **Limit complexity** — max ~15-20 nodes per diagram; split if larger
3. **Group with subgraphs** — reduce visual clutter for related nodes
4. **Consistent link styles** — same style for same relationship type
5. **Use invisible links** (`~~~`) to control layout when nodes misalign
6. **Color with meaning** — use the resolved success, warning, danger, brand, and neutral report colors only when those states are explicit.
7. **Node ID pattern** — use meaningful short IDs (`usr`, `db`, `svc`) not generic (`A`, `B`, `C`)
