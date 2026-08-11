# 泛型 Lambda 与初始化捕获

泛型 Lambda 可以用 `auto` 声明参数，本质上生成带模板调用运算符的闭包。初始化捕获允许在捕获列表中创建成员，尤其适合把只移动对象交给回调。

<!-- example id="cpp14-lambdas" std="c++14" file="main.cpp" kind="single" compilers="all" output="42" -->
```cpp
#include <iostream>
#include <memory>

int main() {
    auto add = [](const auto& left, const auto& right) { return left + right; };
    std::unique_ptr<int> value(new int(40));
    auto calculate = [owned = std::move(value), add]() {
        return add(*owned, 2);
    };

    std::cout << calculate() << '\n';
}
```

初始化捕获的名称属于闭包对象，而不属于外围作用域。移动捕获会使闭包通常只能移动；若把它放入要求可复制目标的 C++14 `std::function`，会发生编译错误。

