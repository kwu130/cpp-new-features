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
