package com.example.ddareungi;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class DdareungiApplication {

	public static void main(String[] args) {
		SpringApplication.run(DdareungiApplication.class, args);
	}

}
