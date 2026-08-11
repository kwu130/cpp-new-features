# 日历、时区与 `chrono` 增强

C++20 增加年、月、日等日历类型，并标准化时区数据库接口。日期算术可在不手写月份天数的情况下完成。

<!-- example id="cpp20-chrono-calendar" std="c++20" file="main.cpp" kind="single" compilers="all" output="days=2" -->
```cpp
#include <chrono>
#include <iostream>

int main() {
    using namespace std::chrono;
    const year_month_day start = 2024y / February / 28d;
    const year_month_day end = 2024y / March / 1d;
    const auto elapsed = sys_days(end) - sys_days(start);
    std::cout << "days=" << elapsed.count() << '\n';
}
```

日历类型能表达暂时无效的日期，必要时调用 `ok()` 检查。时区数据库依赖标准库打包和系统数据，部署前应验证目标环境；跨时区业务应明确使用绝对时间点还是当地民用时间。

## 日历类型的分层

C++20 提供 `year`、`month`、`day` 及其组合。`year_month_day` 便于民用日期字段操作，`sys_days` 是以天为精度的系统时钟时间点，适合做日期差和排序。两者转换时处理闰年和每月天数。

组合语法 `2024y / February / 28d` 构造字段，不一定立即拒绝无效日期；`year_month_day{2023y/February/30d}` 可以存在但 `ok()` 为 false。边界输入必须显式检查，再转换成系统时间点。

`year`、`month`、`day` 是强类型字段，不是普通整数别名。通过 `int(year)`、`unsigned(month/day)` 可显式取数值，`ok()` 检查各字段范围。强类型防止把月份和天数随意混加，却仍允许表示无效组合供解析阶段暂存。

`year_month`、`month_day`、`month_day_last`、`year_month_day_last` 等组合分别表达不同日历概念。选择最贴近业务的信息量，例如年度循环生日可能不需要 year，而“某月最后一天”应使用 last 类型而不是先猜 31。

<!-- example id="cpp20-chrono-last-day" std="c++20" file="main.cpp" kind="single" compilers="all" output="last=2024-2-29" -->
```cpp
#include <chrono>
#include <iostream>

int main() {
    using namespace std::chrono;
    const year_month_day_last last_day = 2024y / February / last;
    const year_month_day date(last_day);

    if (!date.ok()) {
        return 1;
    }
    std::cout << "last=" << int(date.year()) << '-'
              << unsigned(date.month()) << '-'
              << unsigned(date.day()) << '\n';
}
```

`year_month_day_last` 把“该月末日”保存为规则化日历概念，转换到具体 `year_month_day` 时根据闰年得到 29 日。与把 day 固定写成 31 再修正相比，它让月末策略进入类型。

### 连续日表示

`sys_days` 是 `sys_time<days>`，以 system_clock epoch 为基准的连续日时间点；`local_days` 则属于 local_t 时间轴，没有绑定具体 UTC 偏移。日期排序和相差天数通常先转 sys_days，前提是日期有效。

weekday 可从 sys_days/日期构造，支持 `Monday[2]` 之类“某月第几个星期几”以及 `Monday[last]` 组合。排班规则仍要处理节假日和地区日历，标准库只提供公历与星期结构。

## 月份算术与天数算术

“一个月后”和“30 天后”不是同一业务概念。日历类型加 `months` 会保留年月日字段并可能产生无效月末；`sys_days` 加 `days` 则按连续日线推进。账单、订阅和排班必须先定义月末策略，再选择操作。

对 `2024-01-31` 加一个 month 可能得到字段为 `2024-02-31` 的无效 year_month_day；库不会擅自决定夹到 29 日还是滚入三月。业务可检测 `ok()` 后选择 `year/month/last` 夹月末，或转换连续日按固定天数推进。

year_month 加 months 会规范化年月，例如十二月加两个月进入下一年。year 加 years 可能让闰日组合失效，同样需要策略。日历算术保留人类字段语义，而 duration 算术保留连续时间长度。

日期 duration `days` 是固定 24 小时数量，但本地民用一天跨夏令时可能是 23 或 25 小时。计算“明天同一当地时间”与“经过 24 小时”必须选不同时间轴。

## 时区数据库模型

时区不是固定 UTC 偏移。`time_zone` 通过 IANA 等数据库规则把 `sys_time` 映射到 `local_time`，夏令时切换会造成某些本地时间不存在或重复。`zoned_time` 组合时区和时间点，但业务仍要决定歧义选择。

数据库规则会随法律变化。部署环境必须更新 tzdb，并考虑历史数据重放时使用当前规则还是保存当时版本。不是所有 C++20 标准库发行版都完整打包时区数据库，CI 通过编译也不代表生产数据可用。

`get_tzdb()`/`get_tzdb_list()` 访问当前数据库，`locate_zone(name)` 按 IANA 风格名称取得 time_zone，`current_zone()` 查询系统当前区域。指针/引用有效性与 tzdb list 生命周期和 reload 行为相关，长期服务应封装更新策略。

`time_zone::to_local(sys_time)` 的方向通常唯一：绝对时间点在某区域有一个当地表示。`to_sys(local_time)` 可能遇到 nonexistent_local_time 或 ambiguous_local_time；可以指定 `choose::earliest/latest`，但选择必须来自业务需求。

`sys_info` 描述某绝对区间的 UTC offset、save 和 abbreviation；`local_info` 描述本地时间映射的 unique/nonexistent/ambiguous 结果。审计复杂调度时应保留这种结构化状态，而不是只捕获异常文本。

### 闰秒与 UTC 时钟

C++20 chrono 还增加 `utc_clock`、`tai_clock`、`gps_clock`、`file_clock` 及转换设施。system_clock 通常建模 Unix 风格系统时间，闰秒处理与 UTC 时间轴不同。跨时钟转换要使用 `clock_cast`/规定转换关系并确认工具链支持。

`get_leap_second_info` 等设施依赖时区数据库中的闰秒信息。大多数业务时间戳仍选择 sys_time 加时区标识，但科学/通信领域必须明确时间尺度，不能把所有 epoch 整数都叫 UTC。

## 时钟与序列化

跨系统持久化通常保存 UTC 时间点和必要的时区标识，而不是只保存格式化当地时间。耗时测量继续使用 `steady_clock`，不要因新增日历 API 改用可跳变的系统时钟。

只保存 UTC 时间点能恢复瞬间，但不能永远恢复用户原定的“每月当地上午 9 点”规则；重复日程还需保存时区名称和民用字段。只保存当前 offset 也不足以预测未来 DST/法律变化。

序列化应记录单位和 epoch，例如明确为 Unix 毫秒，而不是直接写 `time_since_epoch().count()`；后者的 period/表示类型由 time_point 类型决定。解析时检查范围，避免纳秒时间转换到窄整数溢出。

格式化与解析 chrono 类型的标准支持和 tzdb 一样受库版本影响。协议核心可先用整数 sys_time，用户界面层再做区域格式化，并对不可用时区提供可观测降级。

## 示例解析与测试

示例把闰年 2 月 28 日与 3 月 1 日转换为连续日，正确得到两天。测试应覆盖闰日、月末、DST 跳跃、重复时间、时区规则更新和目标环境缺少 tzdb 的降级路径。

## 权威资料

- [P0355R7：日历与时区](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0355r7.html)
- [工作草案：Time library](https://eel.is/c++draft/time)
- [CPP20 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2020/p2131r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
