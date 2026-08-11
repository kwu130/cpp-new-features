# 类模板实参推导

类模板实参推导（CTAD）根据构造实参和推导指引推断模板参数，减少重复类型书写。

<!-- example id="cpp17-ctad" std="c++17" file="main.cpp" kind="single" compilers="all" output="items=3" -->
```cpp
#include <iostream>
#include <string>
#include <tuple>
#include <utility>

template <typename T>
class Box {
public:
    explicit Box(T value) : value_(std::move(value)) {}
    const T& get() const { return value_; }

private:
    T value_;
};

Box(const char*) -> Box<std::string>;

int main() {
    Box box("items=3");
    std::pair point(2, 5);
    std::tuple record(1, std::string("Ada"));
    (void)point;
    (void)record;
    std::cout << box.get() << '\n';
}
```

CTAD 只省略类模板实参，不会把类模板变成普通类型。自定义推导指引应反映构造函数的自然语义，避免同一调用产生意外类型。

