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

## `chrono` 的强类型时间

`duration<Rep, Period>` 由数值表示类型和编译期单位比例组成。秒、毫秒可以参与受控转换，编译器阻止会丢精度的隐式转换。`time_point<Clock, Duration>` 表示某个时钟纪元后的持续时间；不同 Clock 的时间点不能随意混算。

稳态耗时测量应使用 `steady_clock`，因为它保证单调；`system_clock` 可与日历时间转换，但可能因校时向前或向后跳。类型系统消除了把毫秒误当秒的常见接口错误，却不能替代对时钟语义的选择。

## 随机引擎与分布

引擎是确定性状态机：给定相同种子产生相同原始序列，适合可复现实验。分布把引擎输出映射到均匀整数、正态分布等目标统计分布。将二者分离允许复用引擎并清晰表达概率模型。

固定种子适合测试，生产模拟可用 `random_device` 或外部熵播种，但 `random_device` 是否真正非确定由实现决定。不要对引擎结果直接 `% n`，这可能产生模偏差；使用 `uniform_int_distribution`。

## 正则引擎模型

`std::regex` 在构造时解析模式并建立内部表示，匹配时由实现的正则引擎执行。重复构造同一模式会浪费解析成本，应在安全生命周期内复用。某些模式和引擎可能出现严重回溯成本，正则并不天然是线性时间。

`regex_match` 要求整个输入匹配，`regex_search` 只寻找子串；两者混淆是高频错误。复杂语法、有嵌套结构或需要精确错误恢复时应使用专用解析器。

## 示例解析与工程权衡

主示例显式把 2500 毫秒转换为秒，结果截断为 2；固定种子的掷骰只检查范围而不依赖跨实现的具体映射序列；正则使用整串匹配验证标识符。

代码审查时分别确认时间单位与时钟、随机种子与安全等级、正则匹配范围与最坏性能，不要把三个便利库当作无成本黑盒。

## `chrono` 的转换与舍入

`duration_cast` 在目标周期更粗时会截断，不进行四舍五入。负持续时间的截断方向同样应通过类型转换规则确认。C++17 才加入标准 `floor`、`ceil`、`round` 时间工具，C++11 代码需要显式定义业务舍入策略。

<!-- example id="cpp11-chrono-units" std="c++11" file="main.cpp" kind="single" compilers="all" output="milliseconds=2500, seconds=2" -->
```cpp
#include <chrono>
#include <iostream>

int main() {
    const std::chrono::seconds seconds(2);
    const std::chrono::milliseconds remainder(500);
    const std::chrono::milliseconds total = seconds + remainder;
    const std::chrono::seconds truncated =
        std::chrono::duration_cast<std::chrono::seconds>(total);
    std::cout << "milliseconds=" << total.count()
              << ", seconds=" << truncated.count() << '\n';
}
```

## 随机数的可复现测试

引擎序列由标准算法定义，但分布如何把引擎输出映射到结果在不同实现间不必产生相同序列。因此跨标准库测试不应断言 `uniform_int_distribution` 的某个具体首值；应检查范围、统计性质或把分布封装在项目固定算法中。

<!-- example id="cpp11-random-range" std="c++11" file="main.cpp" kind="single" compilers="all" output="all-in-range=true" -->
```cpp
#include <iostream>
#include <random>

int main() {
    std::mt19937 engine(2024);
    std::uniform_int_distribution<int> dice(1, 6);
    bool valid = true;
    for (int index = 0; index < 100; ++index) {
        const int value = dice(engine);
        valid = valid && value >= 1 && value <= 6;
    }
    std::cout << "all-in-range=" << std::boolalpha << valid << '\n';
}
```

## 正则捕获与匹配结果寿命

`smatch` 内部子匹配通常引用原始字符串的字符区间；原字符串必须在读取匹配结果期间保持有效且不发生使引用失效的修改。频繁匹配同一模式时复用已经构造的 `regex`，避免重复解析。

<!-- example id="cpp11-regex-captures" std="c++11" file="main.cpp" kind="single" compilers="all" output="name=cpp, version=11" -->
```cpp
#include <iostream>
#include <regex>
#include <string>

int main() {
    const std::string text = "cpp-11";
    const std::regex pattern("([a-z]+)-([0-9]+)");
    std::smatch matches;
    if (!std::regex_match(text, matches, pattern) || matches.size() != 3) {
        return 1;
    }
    std::cout << "name=" << matches[1].str()
              << ", version=" << matches[2].str() << '\n';
}
```

## 权威资料

- [时间工具](https://eel.is/c++draft/time)
- [CPP11 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
