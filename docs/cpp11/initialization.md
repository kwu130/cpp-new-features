# 统一初始化、初始化列表与 `nullptr`

花括号初始化为对象、容器和聚合类型提供统一写法，并阻止部分窄化转换。`nullptr` 则替代了容易与整数混淆的 `0` 和 `NULL`。

<!-- example id="cpp11-initialization" std="c++11" file="main.cpp" kind="single" compilers="all" output="3 points, first=1" -->
```cpp
#include <cstddef>
#include <initializer_list>
#include <iostream>
#include <vector>

class Points {
public:
    Points(std::initializer_list<int> values) : values_(values) {}
    std::size_t size() const { return values_.size(); }
    int first() const { return values_.front(); }

private:
    std::vector<int> values_;
};

int main() {
    Points points{1, 2, 3};
    int* pointer = nullptr;
    if (pointer == nullptr) {
        std::cout << points.size() << " points, first=" << points.first() << '\n';
    }
}
```

## 实践建议

新代码优先使用花括号初始化和 `nullptr`。但类同时拥有普通构造函数和 `initializer_list` 构造函数时，花括号会优先匹配后者，应确认这正是预期语义。

窄化写法如 `int value{3.14};` 会在编译期被拒绝，这类反例不放入可执行代码围栏。

