# Changelog

## [0.2.1](https://github.com/Vibrant-Planet-Open-Science/microfvs/compare/v0.2.0...v0.2.1) (2026-10-25)


### Build System

* **deps:** bump anyio from 4.14.0 to 4.14.2 ([#55](https://github.com/Vibrant-Planet-Open-Science/microfvs/issues/55)) ([62cf4e5](https://github.com/Vibrant-Planet-Open-Science/microfvs/commit/62cf4e58e893bf3e75fbb848870a95e97a60d1d7))
* **deps:** bump certifi from 2026.5.20 to 2026.10.19 ([#63](https://github.com/Vibrant-Planet-Open-Science/microfvs/issues/63)) ([c5d5101](https://github.com/Vibrant-Planet-Open-Science/microfvs/commit/c5d510185b7311e5845a1408bda45e92b4dd0599))
* **deps:** bump filelock from 3.29.4 to 4.2.1 ([#62](https://github.com/Vibrant-Planet-Open-Science/microfvs/issues/62)) ([768defa](https://github.com/Vibrant-Planet-Open-Science/microfvs/commit/768defa3b7d72370fcefc8f3c9e92c4ca9305c3b))
* **deps:** bump httpcore2 from 2.4.0 to 2.10.0 ([#53](https://github.com/Vibrant-Planet-Open-Science/microfvs/issues/53)) ([8b73d94](https://github.com/Vibrant-Planet-Open-Science/microfvs/commit/8b73d94ebd266d955d0a31a86ce180d7806df01e))
* **deps:** bump httpx2 from 2.10.0 to 2.12.0 ([#54](https://github.com/Vibrant-Planet-Open-Science/microfvs/issues/54)) ([63c0e9a](https://github.com/Vibrant-Planet-Open-Science/microfvs/commit/63c0e9a76b5d8d1f9e2d4582cf59f50299f68fc3))
* **deps:** bump tornado from 6.5.7 to 6.5.8 ([#52](https://github.com/Vibrant-Planet-Open-Science/microfvs/issues/52)) ([55e881e](https://github.com/Vibrant-Planet-Open-Science/microfvs/commit/55e881ee4840127c8e937fb3beb9659ad076aa03))
* **deps:** bump tornado from 6.5.8 to 6.5.9 ([#60](https://github.com/Vibrant-Planet-Open-Science/microfvs/issues/60)) ([3ed45fb](https://github.com/Vibrant-Planet-Open-Science/microfvs/commit/3ed45fb14b66c2548f5a1f99bec78f7921d5a439))
* **deps:** bump urllib3 from 2.7.0 to 2.8.0 ([#58](https://github.com/Vibrant-Planet-Open-Science/microfvs/issues/58)) ([98ba0d9](https://github.com/Vibrant-Planet-Open-Science/microfvs/commit/98ba0d9bf83f7b2bc47fabfb3e472334b2cc3595))
* **deps:** bump virtualenv from 21.5.1 to 21.14.13 ([#61](https://github.com/Vibrant-Planet-Open-Science/microfvs/issues/61)) ([65ce4c4](https://github.com/Vibrant-Planet-Open-Science/microfvs/commit/65ce4c4ad3c954e6bad301db6dce4097e84c6bf2))

## [0.2.0](https://github.com/Vibrant-Planet-Open-Science/microfvs/compare/v0.1.4...v0.2.0) (2026-09-01)


### ⚠ BREAKING CHANGES

* relicense from CC BY-NC-SA 4.0 to MIT ([#49](https://github.com/Vibrant-Planet-Open-Science/microfvs/issues/49))

### Features

* relicense from CC BY-NC-SA 4.0 to MIT ([#49](https://github.com/Vibrant-Planet-Open-Science/microfvs/issues/49)) ([7f4ec41](https://github.com/Vibrant-Planet-Open-Science/microfvs/commit/7f4ec413affff39adaa316f24064638c0f43ab8d))


### Bug Fixes

* correct OCI provenance labels inherited from the FVS base image ([#50](https://github.com/Vibrant-Planet-Open-Science/microfvs/issues/50)) ([e80427e](https://github.com/Vibrant-Planet-Open-Science/microfvs/commit/e80427ef8ecbd58d15d18449c4b5690eb822f4ed))

## [0.1.4](https://github.com/Vibrant-Planet-Open-Science/microfvs/compare/v0.1.3...v0.1.4) (2026-08-25)


### Features

* deploy via GitOps with a Helm chart rendered by CI ([#46](https://github.com/Vibrant-Planet-Open-Science/microfvs/issues/46)) ([6f1c4cf](https://github.com/Vibrant-Planet-Open-Science/microfvs/commit/6f1c4cfaa5fe9598875a0a1b38d362141753e9d2))


### Bug Fixes

* **ci:** grant the reusable deploy jobs the permissions they request ([#47](https://github.com/Vibrant-Planet-Open-Science/microfvs/issues/47)) ([b71ba4f](https://github.com/Vibrant-Planet-Open-Science/microfvs/commit/b71ba4f0c9f2c75a27fcfe10ebfa50f2b0d047bb))

## [0.1.3](https://github.com/Vibrant-Planet-Open-Science/microfvs/compare/v0.1.2...v0.1.3) (2026-07-29)


### Bug Fixes

* rebuild published image to clear base-image CVEs ([#44](https://github.com/Vibrant-Planet-Open-Science/microfvs/issues/44)) ([ed8f3d8](https://github.com/Vibrant-Planet-Open-Science/microfvs/commit/ed8f3d8bf0752e848ecaaa67a352b1398373be56))

## [0.1.2](https://github.com/Vibrant-Planet-Open-Science/microfvs/compare/v0.1.1...v0.1.2) (2026-07-22)


### Bug Fixes

* patch base-image OS vulnerabilities in container build ([#41](https://github.com/Vibrant-Planet-Open-Science/microfvs/issues/41)) ([6ded574](https://github.com/Vibrant-Planet-Open-Science/microfvs/commit/6ded574da1dd3d1233e24302acad94229b97da3c))

## [0.1.1](https://github.com/Vibrant-Planet-Open-Science/microfvs/compare/v0.1.0...v0.1.1) (2026-07-20)


### Bug Fixes

* bumps FVS_TAG to FS2026.2 ([#38](https://github.com/Vibrant-Planet-Open-Science/microfvs/issues/38)) ([bcb3a62](https://github.com/Vibrant-Planet-Open-Science/microfvs/commit/bcb3a623de47066a6d5f4caabf0ad95931fa0b6a))
