# Complete source provenance

Audit date: 2026-11-01 (Asia/Kolkata). Original worktrees and branches were not edited. Integration is isolated in a local clone; no force push occurred.

| Source | Verified SHA | Publication |
|---|---|---|
| Foundation | `81addc8539d69e5d39df3db545567c833350a87a` | See recorded local/remote inventory; latest frontend verified live |
| Phase 2 backend | `b979ec6fa01974265faf0275f520b8fa41d33017` | See recorded local/remote inventory; latest frontend verified live |
| Phase 2 integrity | `32cdc247a228a23f0e8d087914cb8f377d4acc6f` | See recorded local/remote inventory; latest frontend verified live |
| Main baseline | `a95533838fd4413233ed69edf2ce671260ea8c3a` | See recorded local/remote inventory; latest frontend verified live |
| Phase 3 local acceptance | `ae212b2cdfce755b69ec9a73df15f3907873bf0d` | See recorded local/remote inventory; latest frontend verified live |
| Phase 3 remote | `14d4e6bb055a39ff99e4842c69b2da125c86276c` | See recorded local/remote inventory; latest frontend verified live |
| Latest frontend workplaces | `e73c795f43da934543b421189ecd6b5acbc77172` | See recorded local/remote inventory; latest frontend verified live |
| Older frontend workspaces | `81addc8539d69e5d39df3db545567c833350a87a` | See recorded local/remote inventory; latest frontend verified live |
| Previous local actual frontend | `03cbb014a70aece88ed5f4888ed102c0a690a65f` | See recorded local/remote inventory; latest frontend verified live |
| Phase 4A | `adc216674a5cb0c3f1d82ff4b90450a99df7f47d` | [branch](https://github.com/akilanpl/-Solar-Installation-Management-System/tree/feature/phase4a-support), [draft PR](https://github.com/akilanpl/-Solar-Installation-Management-System/pull/4) |
| Phase 4B | `26a5f129e1eeea5ad772ab4e1b8c5f8f6d43bc3d` | [branch](https://github.com/akilanpl/-Solar-Installation-Management-System/tree/feature/phase4b-warranty-repair), [draft PR](https://github.com/akilanpl/-Solar-Installation-Management-System/pull/5) |
| Phase 4C | `5b1149c8f9805d0ec0edfd36406b48d04d2dd017` | [branch](https://github.com/akilanpl/-Solar-Installation-Management-System/tree/feature/phase4c-finance-admin), [draft PR](https://github.com/akilanpl/-Solar-Installation-Management-System/pull/6) |
| Phase 4D | `292b53d9f431568e950c0ed807c0795155625645` | [branch](https://github.com/akilanpl/-Solar-Installation-Management-System/tree/feature/phase4d-intelligence), [draft PR](https://github.com/akilanpl/-Solar-Installation-Management-System/pull/7) |
| Phase 4E | `1668b6f5e5fc610c7bb6f98b1a6132b077dd832a` | [branch](https://github.com/akilanpl/-Solar-Installation-Management-System/tree/feature/phase4e-enhancements), [draft PR](https://github.com/akilanpl/-Solar-Installation-Management-System/pull/8) |

4A descends from accepted integration baseline; 4B descends from4A;4C/4D/4E share exact4B base. Latest frontend uses Vite with mock state; reviewed visual changes were ported into canonical Next apps/web, not merged as a competing runtime. The original dirty clone is preserved as a binary patch and untracked archive. Valid resurvey/withdrawal/detail routes were retained; obsolete fake payment and hardcoded handoff states were superseded. See DIRTY_SOURCE_RECONCILIATION.md.

Backup bundles outside repository: work/backups/integration-all.bundle, original-all.bundle, complete-preserved-all.bundle. git bundle verify succeeded. Dangling WIP9245b272506fde269ea13d0d05882ccddd224a5f is retained under preserved/dangling-wip in candidate and backup. fsck reported no corruption.

## Bundle checksums

- complete-preserved-all.bundle: `42b8cfd2775ce1d867ae89bb4b1c81b12d1ca90477e24d445cba27702c917f1b`
- integration-all.bundle: `bd59daa5c91c707a139f49202fe9e9cf75f6ff94433ccb80bc3af87088db00af`
- original-all.bundle: `7292cdb276bb10f175717708fc6ce92ed4b130f088cd0eca4a5ba1681ba1939a`

No source missing among expected Phase 4 checkpoints. Source publication used exactly the explicitly approved five SHAs; no integration publication exception granted. See SOURCE_PUBLICATION_AUDIT.md.
