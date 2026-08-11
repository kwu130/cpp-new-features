# `optional`、`variant` 与 `any`

三种词汇类型分别表达“可能没有值”“有限类型集合中的一个值”和“运行期可保存任意可复制类型”。

<!-- example id="cpp17-vocabulary-types" std="c++17" file="main.cpp" kind="single" compilers="all" output="answer=42, tag=cpp17" -->
```cpp
#include <any>
#include <iostream>
#include <optional>
#include <string>
#include <variant>

std::optional<int> parse_answer(bool available) {
    return available ? std::optional<int>{42} : std::nullopt;
}

int main() {
    const auto answer = parse_answer(true);
    std::variant<int, std::string> value = std::string("cpp17");
    std::any metadata = std::string("answer");

    if (!answer || !std::holds_alternative<std::string>(value)) {
        return 1;
    }
    std::cout << std::any_cast<std::string>(metadata) << '=' << *answer
              << ", tag=" << std::get<std::string>(value) << '\n';
}
```

优先选最具体的类型：可缺失用 `optional`，封闭类型集合用 `variant`，只有边界确实开放时才使用 `any`。错误的 `get` 或 `any_cast` 会抛出异常，也可先查询或使用指针形式转换。
