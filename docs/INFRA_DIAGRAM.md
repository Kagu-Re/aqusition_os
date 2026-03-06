# Acquisition Engine — Infrastructure Diagram

*For any business that sells packaged services and benefits from effective booking management.*

## High-Level Architecture

```mermaid
flowchart TB
    subgraph Operators["👤 Operators"]
        CLI[CLI]
        Console[Operator Console<br/>Money Board]
    end

    subgraph ControlPlane["⚙️ Control Plane"]
        API[Public API]
        Reg[Registries<br/>Clients · Templates · Pages]
        Queue[Work Queue]
        Policies[Policies · Gates]
    end

    subgraph Storage["💾 Storage"]
        DB[(SQLite)]
    end

    subgraph Adapters["🔌 Adapter Layer"]
        Content[Content Adapter]
        Publisher[Publisher Adapter]
        Analytics[Analytics Adapter]
    end

    subgraph PublishTargets["📤 Publish Targets"]
        Webflow[Webflow]
        Framer[Framer]
        Static[Tailwind Static]
    end

    subgraph PublishedLayer["📄 Published Layer"]
        LP[Landing Pages]
        Exports[Exports / Payloads]
    end

    subgraph Bots["🤖 Telegram Bots (Local Dev Server)"]
        ServiceBot[Service Bot<br/>Customer-facing<br/>reminders · loyalty · promotions]
        VendorBot[Vendor Bot<br/>Operator-facing]
    end

    subgraph External["🌐 External"]
        Meta[Meta Ads]
        Google[Google Ads]
        Telegram[Telegram API]
    end

    CLI --> API
    Console --> API
    API --> Reg
    API --> Queue
    API --> Policies
    Reg --> DB
    Queue --> DB
    Policies --> DB

    API --> Content
    API --> Publisher
    API --> Analytics

    Content --> Publisher
    Publisher --> Webflow
    Publisher --> Framer
    Publisher --> Static
    Publisher --> LP
    Publisher --> Exports

    Analytics --> DB
    Meta -->|import| Analytics
    Google -->|import| Analytics

    LP -->|"user chooses package"| ServiceBot
    ServiceBot <-->|polling| Telegram
    VendorBot <-->|polling| Telegram
    ServiceBot -->|leads, bookings| DB
    VendorBot -->|booking status, payments| DB
    ServiceBot -->|notify new booking| VendorBot
    Console --> DB
```

## Telegram Bot Logic (Service vs Vendor)

```mermaid
flowchart LR
    subgraph Published["📄 Landing Page (Published)"]
        LP[Landing Page]
    end

    subgraph ServiceBot["🛎️ Service Bot (Customer)"]
        PKG[Package deep link<br/>/start package_xxx]
        FLOW[Booking flow<br/>timeslot, confirm]
        CREATE[Create booking]
        NOTIFY[Notify vendor]
        EXTRA[Reminders · loyalty · promotions]
    end

    subgraph VendorBot["⚙️ Vendor Bot (Operator)"]
        CMD[/bookings<br/>/paid /complete]
        RECV[Receives booking<br/>notifications]
    end

    subgraph DB["💾 Database"]
        DBSTOR[(leads, bookings<br/>conversations,<br/>payment_intents)]
    end

    subgraph Users["👥 Users"]
        Customer[Customer]
        Vendor[Vendor / Operator]
    end

    LP -->|"click package"| Customer
    Customer -->|t.me/bot?start=package_xxx| PKG
    PKG --> FLOW --> CREATE --> NOTIFY
    EXTRA -.->|optional| Customer
    CREATE --> DBSTOR
    NOTIFY --> RECV
    RECV --> Vendor
    Vendor -->|"/bookings, /paid"| CMD
    CMD --> DBSTOR
```

## Data Flow (Lead Acquisition)

```mermaid
flowchart LR
    subgraph Inbound["Inbound"]
        Ads[Meta/Google Ads]
    end

    subgraph Published["📄 Published Layer"]
        LP[Landing Page]
    end

    subgraph Bots["🤖 Telegram"]
        ServiceBot[Service Bot]
        VendorBot[Vendor Bot]
    end

    subgraph Backend["Backend"]
        Publish[Publish]
        Track[Track Events]
        Board[Money Board]
    end

    subgraph Outbound["Outbound"]
        Lead[Lead/Customer]
    end

    Ads -->|click| LP
    Publish --> LP
    LP -->|"user chooses option"| ServiceBot
    ServiceBot -->|creates booking| Lead
    ServiceBot -->|notify| VendorBot
    LP --> Track
    Track --> Board
```

## Component Overview

| Layer | Components |
|-------|------------|
| **Operators** | CLI, Operator Console, Money Board |
| **Control Plane** | Public API, Registries, Work Queue, Policies |
| **Storage** | SQLite (clients, pages, events, ad_stats, bookings, leads, chat) |
| **Adapters** | Content, Publisher (Webflow/Framer/Static), Analytics |
| **Published Layer** | Landing pages (user chooses package → redirects to Service Bot) |
| **Service Bot** | Customer-facing. Package deep links, booking flow, leads/bookings, notifies Vendor Bot. Supports reminders, loyalty, promotions |
| **Vendor Bot** | Operator-facing. /bookings, /paid, /complete. Receives notifications from Service Bot |
| **External** | Meta Ads, Google Ads, Telegram API |

---

*Render this Mermaid in [mermaid.live](https://mermaid.live) or any Markdown viewer that supports Mermaid to export as PNG/SVG for LinkedIn.*
