package com.example.ddareungi;

import com.example.ddareungi.api.bike.BikeApiService;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class DdareungiApplication {

	public static void main(String[] args) {
		SpringApplication.run(DdareungiApplication.class, args);
	}

}
