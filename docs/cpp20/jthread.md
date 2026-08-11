# `jthread`、停止令牌与协作取消

`jthread` 析构时自动请求停止并连接线程。若可调用对象首参数接受 `stop_token`，它就能响应协作式取消。

<!-- example id="cpp20-jthread" std="c++20" file="main.cpp" kind="single" compilers="all" output="42" -->
```cpp
#include <iostream>
#include <stop_token>
#include <thread>

int main() {
    int result = 0;
    std::jthread worker([&result](std::stop_token token) {
        if (!token.stop_requested()) {
            result = 42;
        }
    });
    worker.join();
    std::cout << result << '\n';
}
```

停止请求不会强行终止线程，任务必须在合适位置查询令牌或注册回调。自动 `join` 改善异常安全，但持锁析构 `jthread` 仍可能造成死锁。

