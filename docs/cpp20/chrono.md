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

## 月份算术与天数算术

“一个月后”和“30 天后”不是同一业务概念。日历类型加 `months` 会保留年月日字段并可能产生无效月末；`sys_days` 加 `days` 则按连续日线推进。账单、订阅和排班必须先定义月末策略，再选择操作。

## 时区数据库模型

时区不是固定 UTC 偏移。`time_zone` 通过 IANA 等数据库规则把 `sys_time` 映射到 `local_time`，夏令时切换会造成某些本地时间不存在或重复。`zoned_time` 组合时区和时间点，但业务仍要决定歧义选择。

数据库规则会随法律变化。部署环境必须更新 tzdb，并考虑历史数据重放时使用当前规则还是保存当时版本。不是所有 C++20 标准库发行版都完整打包时区数据库，CI 通过编译也不代表生产数据可用。

## 时钟与序列化

跨系统持久化通常保存 UTC 时间点和必要的时区标识，而不是只保存格式化当地时间。耗时测量继续使用 `steady_clock`，不要因新增日历 API 改用可跳变的系统时钟。

## 示例解析与测试

示例把闰年 2 月 28 日与 3 月 1 日转换为连续日，正确得到两天。测试应覆盖闰日、月末、DST 跳跃、重复时间、时区规则更新和目标环境缺少 tzdb 的降级路径。

## 权威资料

- [P0355R7：日历与时区](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0355r7.html)
- [CPP20 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2020/p2131r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
