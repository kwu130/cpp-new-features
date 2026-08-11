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

