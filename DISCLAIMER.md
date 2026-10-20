# Disclaimer

**中文版本为正式文本；英文版本仅为便利性翻译，如中英文存在歧义或冲突，以中文版本为准。**

TSecBench Agent is an educational and research project provided "as is". It contains
offensive-security skills, scripts, payloads, and tooling. Read the Chinese text below,
which is the authoritative version. This document is not legal advice.

## 1. Permitted use

1. The skills, scripts, payloads, and tools in this repository may be used only against
   systems that you own or for which you hold prior written authorization, and in CTF
   competitions, evaluation environments, authorized penetration tests, and defensive
   research.
2. Scanning, intruding into, interfering with, or obtaining data from systems without
   authorization may violate the laws of the People's Republic of China — including the
   Cybersecurity Law, the Data Security Law, and the Criminal Law — as well as other
   applicable laws. Anyone who does so bears the consequences alone.
3. Users are responsible for determining whether possession, distribution, and use of
   these tools and techniques is lawful in their own jurisdiction.

## 2. No responsibility for third-party misuse

1. The authors, maintainers, and contributors (the "maintainers") are not affiliated
   with, do not consent to, authorize, assist, or endorse any unlawful or non-compliant
   use of this repository or its contents by any third party.
2. Any third party that uses this repository or its contents for non-compliant purposes
   is solely responsible for that use. The maintainers accept no direct or indirect
   responsibility for it.
3. The maintainers make no express or implied warranty as to the accuracy,
   completeness, fitness, or legality of the contents.

## 3. Restrictions on competitive use

1. Except for the maintainers of this project and members they authorize in writing
   (the "first party"), no third party may **directly use this repository** to
   participate in competitions, evaluations, or contests of the same kind as the
   competition this project targets ("similar competitions").
2. "Direct use" means using the repository's content verbatim, or with only minor
   adjustments, in a competition — including packaging the repository itself as a
   competition image, or using its prompts and skill configuration as they are.
3. "Similar competitions" means competitions and evaluations that assess autonomous
   agent offensive-security, penetration-testing, or security-agent capability,
   including but not limited to the 3rd Tencent Cloud Intelligent Attack and Defense
   Challenge and its subsequent editions, and comparable events run by other platforms
   or organizations.
4. **Derivative works are not restricted.** Works that a third party creates by
   modifying, adapting, or building on this repository may be used and entered into
   competitions freely; this repository adds no such restriction to them.
5. This section applies only to first-party content and to the assembled work. Third
   party content listed in `THIRD_PARTY_NOTICES.md` remains licensed by its upstream
   rights holders; users must confirm that their use complies with the upstream
   licenses.
6. This section is a condition of use. Obtaining, copying, deploying, or using this
   repository constitutes acceptance of this section.

## 4. Third-party content

This repository includes third-party content distributed under its own licenses (see
`THIRD_PARTY_NOTICES.md`). That content is licensed by its upstream rights holders, and
the maintainers accept no responsibility for the consequences of its use.

## 5. Limitation of liability

To the maximum extent permitted by applicable law, the maintainers are not liable for
any direct, indirect, incidental, special, or consequential damages arising from the use
of, or inability to use, this repository, including loss of data, business interruption,
or legal disputes. This disclaimer does not modify, replace, or limit the warranty
disclaimer and limitation of liability in the Apache License 2.0; in case of conflict,
the Apache License 2.0 prevails.

## 6. Governing law and jurisdiction

This disclaimer, and any dispute arising out of or relating to this repository, are
governed by the laws of the People's Republic of China (excluding the laws of Hong Kong,
Macao, and Taiwan). Disputes shall be submitted to the competent people's court at the
maintainers' domicile (Jiangmen, Guangdong Province, People's Republic of China).

## 7. Miscellaneous

This disclaimer is not legal advice. If you intend to use this repository in a
commercial or regulated context, consult a qualified legal professional.

---

# 免责声明（正式文本）

TSecBench Agent 是面向教学、研究、CTF 竞赛与授权安全测试的项目，按“现状”提供。本仓库包含攻防技能、脚本、载荷与工具。本文件不构成法律意见。

## 一、允许的使用范围

1. 本仓库所含技能、脚本、载荷与工具，仅可用于你拥有或已取得**事先书面授权**的系统，以及 CTF 竞赛、评测环境、授权渗透测试与防御研究。
2. 未经授权对他人系统进行扫描、入侵、干扰或数据获取，可能违反《中华人民共和国网络安全法》《中华人民共和国数据安全法》《中华人民共和国刑法》等法律法规及其他适用法律；由此产生的一切后果由行为人自行承担。
3. 使用者应自行确认其所在司法辖区对相关工具与技术的持有、传播和使用是否合法。

## 二、与他方非合规使用无关

1. 本仓库作者、维护者与贡献者（以下统称“维护者”）**与任何第三方使用本仓库或其内容从事违法违规行为无关**；维护者不构成对该等行为的同意、授权、协助或背书。
2. 任何第三方将本仓库或其内容用于非合规用途，均由该第三方**独立承担全部责任**；维护者不承担任何直接或间接责任。
3. 维护者不对本仓库内容的准确性、完整性、适用性或合法性作出任何明示或默示保证。

## 三、竞赛使用限制

1. 除本项目维护团队及其书面授权的成员（以下称“第一方”）外，任何第三方**不得直接使用本仓库**参加与本项目目标赛事同类的比赛、评测或竞赛（以下称“同类竞赛”）。
2. “直接使用”指将本仓库内容原样使用，或仅作少量调整后用于参赛，包括将本仓库本身打包为参赛镜像、直接照用其提示词与技能编排配置参赛。
3. “同类竞赛”指以自主 Agent 攻防能力、渗透测试能力或安全智能体能力为评测对象的比赛与评测活动，包括但不限于第三届腾讯云智能攻防挑战赛及其后续赛事，以及其他平台或机构举办的同类型赛事。
4. **衍生物不受本限制。** 第三方基于本仓库自行修改、演绎或再创作所形成的作品，可以自行使用并参加竞赛；本仓库不对该等衍生物追加本条限制。
5. 本条限制仅约束第一方内容及其构成的整体作品。第三方内容（`THIRD_PARTY_NOTICES.md` 所列）仍由其上游权利人按其许可证授权；使用者应自行确认其使用符合上游许可。
6. 本条款为使用条件。获取、复制、部署或使用本仓库，即视为接受本条款。

## 四、第三方内容

本仓库包含按各自许可证分发的第三方内容（详见 `THIRD_PARTY_NOTICES.md`）。该等内容由其上游权利人授权，维护者不对其使用后果承担责任。

## 五、责任限制

在适用法律允许的最大范围内，维护者不对因使用或无法使用本仓库而产生的任何直接、间接、附带、特殊或后果性损害承担责任，包括但不限于数据丢失、业务中断或法律纠纷。本免责声明不改变、不替代亦不限制 Apache License 2.0 中的保证免除与责任限制条款；如二者存在冲突，以 Apache License 2.0 为准。

## 六、适用法律与争议解决

本免责声明及因本仓库产生或与之相关的争议，适用**中华人民共和国法律**（不含香港特别行政区、澳门特别行政区及台湾地区法律）。争议应提交维护者住所地（广东省江门市）有管辖权的人民法院解决。

## 七、其他

本免责声明不构成法律意见。如你计划将本仓库用于商业或受监管场景，请咨询专业法律人士。

**中文版本为正式文本；英文版本仅为便利性翻译，如中英文存在歧义或冲突，以中文版本为准。**
