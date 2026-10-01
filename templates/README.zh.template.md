<!--
  中文门面模板。占位符用 <尖括号> 标出，全部替换掉。
  README.en.md 必须是本文的逐节镜像（章节数量与顺序一一对应）。
  规则见 SKILL.md §3。
-->

<div align="center">

<h1><项目名></h1>

<b><平台或品类关键词，用 · 分隔></b><br>
<一句话价值主张：谁 + 做什么 + 得到什么>

**简体中文** | [English](./README.en.md)

<a href="../../releases/latest"><img src="https://img.shields.io/github/v/release/<OWNER>/<REPO>?style=flat-square&label=Release&color=ff4d6d" alt="Release"></a>
<a href="../../releases"><img src="https://img.shields.io/github/downloads/<OWNER>/<REPO>/total?style=flat-square&label=Downloads&color=ffd166" alt="Downloads"></a>
<a href="../../stargazers"><img src="https://img.shields.io/github/stars/<OWNER>/<REPO>?style=flat-square&label=Stars&color=06d6a0" alt="Stars"></a>
<a href="../../forks"><img src="https://img.shields.io/github/forks/<OWNER>/<REPO>?style=flat-square&label=Forks&color=4cc9f0" alt="Forks"></a>
<a href="../../issues"><img src="https://img.shields.io/github/issues/<OWNER>/<REPO>?style=flat-square&label=Issues" alt="Issues"></a>

<br>

<a href="#-下载安装"><img src="https://img.shields.io/badge/平台-Windows-0078d4?style=flat-square&logo=windows&logoColor=white" alt="Windows"></a>
<a href="#-下载安装"><img src="https://img.shields.io/badge/平台-Android-3ddc84?style=flat-square&logo=android&logoColor=white" alt="Android"></a>
<img src="https://img.shields.io/badge/<语言>-<版本>-3776ab?style=flat-square" alt="Language">
<img src="https://img.shields.io/badge/许可证-保留所有权利-8b8b8b?style=flat-square" alt="License">

</div>

---

<3~5 行定位说明：这是什么、跑在哪里、数据是否外传。用**加粗**突出关键承诺。>

> ⚠️ **<最要命的前提条件，一句一个>**
> <例如：某平台需要自备代理 / 某功能需要额外依赖 / 输入格式有硬性要求>
> 详见 [<章节名>](#<锚点>)。

## 🎬 它长什么样

<div align="center">
<img src="./docs/screenshot-result-zh.png" width="880" alt="使用结果">
<br>
<sub><这张图在演示什么：输入 → 处理 → 得到什么></sub>
</div>

<br>

<div align="center">
<img src="./docs/screenshot-home-zh.png" width="880" alt="初始界面">
<br>
<sub><初始状态说明></sub>
</div>

<若有前后对比图，用一段引导语 + 对比图 + <details> 放可复核依据>

## 📥 下载安装

到 [**Releases**](../../releases/latest) 页面下载。

### <平台 A>

| | |
| --- | --- |
| 文件 | `<资产文件名>`（<大小>） |
| 依赖 | <有 / 无 —— 说明清楚> |

1. <步骤一>
2. <步骤二>

> ⚠️ <该平台特有的坑，例如杀软误报、需要允许未知来源>

### <平台 B>

<同上>

### 从源码运行

```bash
git clone https://github.com/<OWNER>/<REPO>.git
cd <REPO>
<安装与启动命令>
```

## ✨ <能力矩阵>

| <维度> | <能力 1> | <能力 2> | 上限 | 还支持 |
| --- | --- | --- | --- | --- |
| **<对象 1>** | ✅ | ✅ | <实测上限> | <附加能力> |
| **<对象 2>** | ✅ | — | <实测上限> | <附加能力> |

## ⚙️ 三步开始用

1. <第一步>
2. <第二步>
3. <第三步>

**支持的输入形态**

| 类型 | 可接受的写法 |
| --- | --- |
| <类型 1> | `<示例>` |

## ⚠️ <前提条件与能力边界>（重要）

> 这节是**建立信任的地方**，也是挡 issue 的地方。明确写出做不到什么。
> 每条尽量带实测记录。

### <限制 1>

<说明 + 实测证据 + 用户该怎么做>

### <限制 2>

| <档位> | 前提 |
| --- | --- |
| <低档> | 无需 <条件> |
| <高档> | 需要 <条件> |

**实测澄清（<年月>）**：<把「流传的说法」与「实测结果」分开写；不符就直说「这个说法不成立」>

## 🧱 技术栈

| | |
| --- | --- |
| 后端 | <...> |
| 前端 | <...> |
| 依赖 | <...> |
| 打包 | <...> |

## 🗂 项目结构

```
<文件>                 <一句话职责>
docs/                  README 用的截图
```

## 🔌 REST API

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| `POST` | `/api/...` | <...> |

交互式接口文档：服务起来后打开 `http://127.0.0.1:<PORT>/docs`。

## ❓ 常见问题

<details>
<summary><b><问题一句话></b></summary>

<回答：先说原因，再说怎么排查，最后给解法。>
</details>

<details>
<summary><b><问题二></b></summary>

<...>
</details>

## 📄 合规与免责

- <内容>的**著作权归原作者及平台所有**。
- 请仅用于**个人学习与技术交流**，不要用于商业或侵权用途；<若有下载内容，24 小时内删除>。
- 擅自传播他人作品可能违反平台服务协议及相关法律法规，**风险由使用者自行承担**。
- <本工具不绕过付费内容之类的边界声明>

## 📮 联系

| | |
| --- | --- |
| 问题反馈 | [Issues](../../issues) |
| 仓库 | <https://github.com/<OWNER>/<REPO>> |

## ⭐ Star 历史

<a href="https://star-history.com/#<OWNER>/<REPO>&Timeline">
  <img src="https://api.star-history.com/svg?repos=<OWNER>/<REPO>&type=Timeline" alt="Star History" width="620">
</a>

## 📄 许可

<若不开源：本仓库**未附带开源许可证**（All rights reserved）。你可以自由下载与使用发行版；如需在其它项目中复用代码或商用，请先通过 Issues 联系作者。>

<div align="center">
<sub>本 README 采用「<a href="./README.en.md">简体中文</a> / English」双语，可用顶部链接切换。</sub>
</div>
