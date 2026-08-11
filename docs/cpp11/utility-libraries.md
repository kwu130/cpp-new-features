# `chrono`、随机数与正则表达式

`chrono` 提供带单位的时间类型，`<random>` 将随机引擎与分布分离，正则库用于模式匹配。

<!-- example id="cpp11-utility-libraries" std="c++11" file="main.cpp" kind="single" compilers="all" output="valid=true, seconds=2" -->
```cpp
#include <chrono>
#include <iostream>
#include <random>
#include <regex>
#include <string>

int main() {
    const std::chrono::milliseconds elapsed(2500);
    const std::chrono::seconds seconds =
        std::chrono::duration_cast<std::chrono::seconds>(elapsed);

    std::mt19937 engine(1234);
    std::uniform_int_distribution<int> distribution(1, 6);
    const int roll = distribution(engine);
    const bool in_range = roll >= 1 && roll <= 6;

    const std::regex identifier("[A-Za-z_][A-Za-z0-9_]*");
    const bool valid = in_range && std::regex_match(std::string("value_1"), identifier);
    std::cout << std::boolalpha << "valid=" << valid << ", seconds=" << seconds.count() << '\n';
}
```

持续时间转换可能截断低位精度。不要用 `rand()` 实现需要明确分布的随机逻辑；安全令牌则需要密码学随机源，标准伪随机引擎并不适用。正则表达式便于描述模式，但复杂解析任务应考虑专用解析器。

