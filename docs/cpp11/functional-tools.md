# `tuple`、类型萃取与可调用对象

`tuple` 表示固定数量的异构值；类型萃取支持编译期类型查询与转换；`function` 提供统一的类型擦除调用接口。

<!-- example id="cpp11-functional-tools" std="c++11" file="main.cpp" kind="single" compilers="all" output="Ada:42" -->
```cpp
#include <functional>
#include <iostream>
#include <string>
#include <tuple>
#include <type_traits>

std::string describe(const std::string& name, int score) {
    return name + ':' + std::to_string(score);
}

int main() {
    typedef std::tuple<std::string, int> Record;
    Record record("Ada", 42);
    static_assert(std::tuple_size<Record>::value == 2, "Record has two fields");
    static_assert(std::is_integral<std::tuple_element<1, Record>::type>::value,
                  "the score is integral");

    std::function<std::string(const std::string&)> formatter =
        std::bind(describe, std::placeholders::_1, std::get<1>(record));
    std::cout << formatter(std::get<0>(record)) << '\n';
}
```

`std::function` 可能产生分配和间接调用开销；无需存储异构可调用对象时优先使用模板或具体 Lambda 类型。新代码中 Lambda 通常比复杂的 `bind` 表达式更直观。

