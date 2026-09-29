"""内置中文评测语料：全部由本项目的合法假数据生成器合成。

为什么合成而不是收录真实文档：真实文档带版权与二次泄露风险；
合成语料的 gold 标注由构造过程精确已知，指标没有标注噪声。
缺点：分布窄于真实业务文档，结果只代表"格式级能力"，README 中如实声明。
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .. import checksum
from ..data import FAKE_GIVEN_CHARS, SURNAMES
from ..types import Entity

_rng = random.Random(20260927)


def _fake_name() -> str:
    return _rng.choice(SURNAMES) + "".join(_rng.choice(FAKE_GIVEN_CHARS) for _ in range(_rng.randint(1, 2)))


def _fake_phone() -> str:
    prefixes = sorted(checksum.MOBILE_SEGMENTS)
    return _rng.choice(prefixes) + "".join(str(_rng.randint(0, 9)) for _ in range(8))


def _fake_id() -> str:
    return checksum.make_fake_id_card(_rng)


def _fake_bank() -> str:
    return checksum.make_fake_bank_card(_rng, _rng.choice(("621700", "622202", "622260")))


def _fake_uscc() -> str:
    return checksum.make_fake_uscc(_rng, _rng.choice(("9111", "9133", "5211")))


@dataclass
class DocBuilder:
    doc_id: str
    title: str
    parts: list[str] = field(default_factory=list)
    gold: list[Entity] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "".join(self.parts)

    def t(self, piece: str) -> DocBuilder:
        self.parts.append(piece)
        return self

    def pii(self, entity_type: str, value: str, score: float = 0.95, source: str = "checksum") -> DocBuilder:
        start = len(self.text)
        self.parts.append(value)
        self.gold.append(
            Entity(
                type=entity_type,
                start=start,
                end=start + len(value),
                text=value,
                score=score,
                source=source,
            )
        )
        return self

    def build(self) -> Doc:
        return Doc(doc_id=self.doc_id, title=self.title, text=self.text, gold=list(self.gold))


@dataclass
class Doc:
    doc_id: str
    title: str
    text: str
    gold: list[Entity]


def _doc_rental() -> Doc:
    b = DocBuilder("rental", "租房合同")
    name = _fake_name()
    phone = _fake_phone()
    idcard = _fake_id()
    bank = _fake_bank()
    b.t("房屋租赁合同\n出租方（甲方）：").pii("PERSON_NAME", name, 0.95).t("\n联系电话：").pii(
        "PHONE", phone
    ).t("\n身份证号：").pii("ID_CARD", idcard)
    b.t("\n房屋坐落于北京市海淀区中关村大街27号3号楼501室，月租金伍仟元整。")
    b.t("\n租金请汇入甲方银行账户：").pii("BANK_CARD", bank)
    b.t("。押金叁仟元，退租时结清水电燃气费。本合同一式两份。")
    b.t("订单查询编号 8861720455312 仅用于内部检索。")
    return b.build()


def _doc_hospital() -> Doc:
    b = DocBuilder("hospital", "医院挂号单")
    name = _fake_name()
    idcard = _fake_id()
    phone = _fake_phone()
    b.t("XX市第一人民医院 门诊挂号单\n患者姓名：").pii("PERSON_NAME", name, 0.95)
    b.t("\n身份证号：").pii("ID_CARD", idcard).t("\n联系电话：").pii("PHONE", phone)
    b.t("\n就诊科室：呼吸内科；就诊时间：周四上午。")
    b.t("\n家庭住址：").pii("ADDRESS", "江苏省南京市鼓楼区中山北路8号2幢202室", 0.9, "context")
    b.t("\n温馨提示：请携带医保卡按时就诊。发票号 0341728596 供报销使用。")
    return b.build()


def _doc_express() -> Doc:
    b = DocBuilder("express", "快递面单")
    name = _fake_name()
    phone = _fake_phone()
    b.t("顺丰速运\n收件人：").pii("PERSON_NAME", name, 0.95).t("  ").pii("PHONE", phone)
    b.t("\n收件地址：").pii("ADDRESS", "浙江省杭州市西湖区文三路120号星光大厦12层", 0.9, "context")
    b.t("\n内件品名：文件资料。运单号 SF1234567890123。")
    return b.build()


def _doc_support() -> Doc:
    b = DocBuilder("support", "客服聊天记录")
    name = _fake_name()
    phone = _fake_phone()
    email = "user.ming@example.cn"
    b.t("客服：您好，请问有什么可以帮您？\n用户：我手机换号了，改成 ").pii("PHONE", phone)
    b.t("，麻烦更新联系方式。\n客服：好的，请问您的会员姓名？\n用户：").pii("PERSON_NAME", name, 0.95)
    b.t("。绑定邮箱 ").pii("EMAIL", email, 0.9).t(" 也可以。")
    b.t("\n客服：已记录，会员卡号 5003820001 请妥善保管。")
    return b.build()


def _doc_meeting() -> Doc:
    b = DocBuilder("meeting", "会议纪要")
    a = _fake_name()
    bb = _fake_name()
    uscc = _fake_uscc()
    tel = "010-65542317"
    b.t("项目协调会纪要\n出席：").pii("PERSON_NAME", a, 0.95).t("、").pii("PERSON_NAME", bb, 0.95)
    b.t(" 等五人。\n合作方全称：北京示例科技有限公司（统一社会信用代码：").pii("USCC", uscc)
    b.t("）。\n前台电话：").pii("LANDLINE", tel, 0.85)
    b.t("。会议决定下周三前提交需求文档，编号 MN-2026-0091。")
    return b.build()


def _doc_resume() -> Doc:
    b = DocBuilder("resume", "个人简历")
    name = _fake_name()
    phone = _fake_phone()
    idcard = _fake_id()
    email = "career.dev2026@example.com"
    b.t("个人简历\n姓名：").pii("PERSON_NAME", name, 0.95).t("\n手机：").pii("PHONE", phone)
    b.t("\n身份证：").pii("ID_CARD", idcard).t("\n邮箱：").pii("EMAIL", email, 0.9)
    b.t("\n求职意向：后端开发工程师。工作年限五年，熟悉分布式系统。现居").pii(
        "ADDRESS", "上海市浦东新区张江路333弄12号202室", 0.9, "context"
    )
    b.t("。\n期望薪资面议。")
    return b.build()


def _doc_repayment() -> Doc:
    b = DocBuilder("repayment", "还款提醒短信")
    name = _fake_name()
    phone = _fake_phone()
    idcard = _fake_id()
    b.t("【XX消费金融】尊敬的").pii("PERSON_NAME", name, 0.95)
    b.t("，您本分期账单将于10日后到期，尾号8217账户应还3,200.00元。客服 ").pii("PHONE", phone)
    b.t("。逾期将影响征信记录（证件号 ").pii("ID_CARD", idcard)
    b.t(" 对应账户）。回T退订。")
    return b.build()


def _doc_property() -> Doc:
    b = DocBuilder("property", "物业通知")
    name = _fake_name()
    phone = _fake_phone()
    plate = "京A·D1289"
    b.t("物业服务中心通知\n3号楼502室业主 ").pii("PERSON_NAME", name, 0.95)
    b.t(" 您的车位欠费，登记车牌 ").pii("LICENSE_PLATE", plate, 0.85)
    b.t("，请于本周内缴纳。物业电话 ").pii("PHONE", phone)
    b.t("。地址：").pii("ADDRESS", "成都市锦江区红星路三段99号银石广场", 0.9, "context")
    b.t("。")
    return b.build()


def _doc_insurance() -> Doc:
    b = DocBuilder("insurance", "保险回访记录")
    name = _fake_name()
    idcard = _fake_id()
    phone = _fake_phone()
    b.t("回访专员：您好，这里是XX人寿，请问是 ").pii("PERSON_NAME", name, 0.95)
    b.t(" 女士本人吗？\n客户：是我。\n专员：请提供身份证号核实：").pii("ID_CARD", idcard)
    b.t("。\n客户：（已提供）\n专员：收到，回访号码 ").pii("PHONE", phone)
    b.t("，保单号 P2026889912004417 已生效。")
    return b.build()


def _doc_hiring() -> Doc:
    b = DocBuilder("hiring", "应聘登记表")
    name = _fake_name()
    phone = _fake_phone()
    idcard = _fake_id()
    email = "job.apply2026@example.org"
    b.t("应聘登记表\n姓名：").pii("PERSON_NAME", name, 0.95).t("\n联系电话：").pii("PHONE", phone)
    b.t("\n身份证号：").pii("ID_CARD", idcard).t("\n电子邮箱：").pii("EMAIL", email, 0.9)
    b.t("\n应聘岗位：数据分析师。到岗时间：一个月内。")
    return b.build()


def _doc_hotel() -> Doc:
    b = DocBuilder("hotel", "酒店入住登记")
    name = _fake_name()
    idcard = _fake_id()
    phone = _fake_phone()
    passport = "E" + f"{_rng.randint(10_000_000, 99_999_999)}"
    plate = "沪BL6K82"
    b.t("入住登记单\n宾客姓名：").pii("PERSON_NAME", name, 0.95)
    b.t("\n证件一：").pii("ID_CARD", idcard).t("\n证件二：").pii("PASSPORT", passport, 0.85)
    b.t("\n联系电话：").pii("PHONE", phone).t("\n车牌号：").pii("LICENSE_PLATE", plate, 0.85)
    b.t("\n房型：大床房两晚，房间号 1208。存放贵重物品请使用客房保险箱。")
    return b.build()


def _doc_corp() -> Doc:
    b = DocBuilder("corp", "企业对账函")
    uscc = _fake_uscc()
    bank = _fake_bank()
    b.t("询证函\n致：深圳市示例贸易有限公司（统一社会信用代码：").pii("USCC", uscc)
    b.t("）\n贵司在我行账户 ").pii("BANK_CARD", bank)
    b.t(" 截至2026年9月30日余额为人民币 1,203,500.00 元。联系电话 ").pii("LANDLINE", "021-63321588", 0.85)
    b.t("。\n对账编号 RC-7712039485。")
    return b.build()


def _doc_prose_notice() -> Doc:
    """散文体（长段落叙述）：验证非结构化文本上的表现。"""
    b = DocBuilder("prose_notice", "社区通知（散文体）")
    name = _fake_name()
    phone = _fake_phone()
    b.t("各位居民：接街道办通知，本周六上午将开展燃气安全入户检查。")
    b.t("负责本片区的检查员为").pii("PERSON_NAME", name, 0.95)
    b.t("，如需改约时间请提前致电").pii("PHONE", phone)
    b.t("联系。检查内容包含灶具软管老化、烟道通畅与一氧化碳报警器安装情况，全程约二十分钟，不收取任何费用。")
    b.t("望大家相互转告，并提前清理楼道堆物，配合检查人员入户。特此通知。")
    return b.build()


def _doc_prose_lost() -> Doc:
    """散文体（失物招领）：订单号等 6 位数字不应被误判为邮编。"""
    b = DocBuilder("prose_lost", "失物招领（散文体）")
    name = _fake_name()
    b.t("昨晚八时左右，一位").pii("PERSON_NAME", name, 0.95)
    b.t("先生在2号线列车上遗失黑色双肩包一只，内有笔记本电脑与Books《城市建筑读本》一册。")
    b.t("拾到者请与失主电话联系，也可将物品送至地铁服务站，报失物编号 338172 即可核对。")
    b.t("感谢您的善意，愿善意在城市里流动。")
    return b.build()


_BUILDERS = [
    _doc_rental,
    _doc_hospital,
    _doc_express,
    _doc_support,
    _doc_meeting,
    _doc_resume,
    _doc_repayment,
    _doc_property,
    _doc_insurance,
    _doc_hiring,
    _doc_hotel,
    _doc_corp,
    _doc_prose_notice,
    _doc_prose_lost,
]


def build_corpus() -> list[Doc]:
    return [builder() for builder in _BUILDERS]
